import random
from core.models import Unit
from logic.clash_flow import ClashFlowMixin


class ClashSystem(ClashFlowMixin):
    """
    Уровень 3: Управление боем (Дирижер).
    - Расчет инициативы и перенаправлений
    - Сортировка действий
    - Запуск соответствующего сценария (Clash/One-Sided)
    """

    def __init__(self):
        self.logs = []

    def log(self, message):
        self.logs.append(message)

    @staticmethod
    def calculate_redirections(attacker: Unit, defender: Unit):
        """
        Перенаправляет цель защитника на атакующего, если атакующий быстрее.
        Приоритет: 1. Aggro, 2. Самый медленный.
        """
        interceptors = {}
        for i, s1 in enumerate(attacker.active_slots):
            # === ВАЖНО: Если слот имеет флаг prevent_redirection (Ликорис), он не перехватывает ===
            if s1.get('prevent_redirection'):
                continue

            target_idx = s1.get('target_slot', -1)
            if target_idx != -1 and target_idx < len(defender.active_slots):
                s2 = defender.active_slots[target_idx]
                # Перехват возможен только если мы быстрее цели
                if s1['speed'] > s2['speed']:
                    if target_idx not in interceptors: interceptors[target_idx] = []
                    interceptors[target_idx].append(i)

        for def_idx, atk_indices in interceptors.items():
            s2 = defender.active_slots[def_idx]

            # Если цель сама "неперенаправляемая" (Ликорис), то её нельзя заставить сменить цель
            if s2.get('prevent_redirection'):
                continue

            aggro_indices = [idx for idx in atk_indices if attacker.active_slots[idx].get('is_aggro')]

            chosen_idx = None
            if aggro_indices:
                # Если есть Aggro, берем самого медленного из них
                chosen_idx = min(aggro_indices, key=lambda idx: attacker.active_slots[idx]['speed'])
            else:
                # Иначе берем самого медленного из всех (стандартная механика LoR)
                chosen_idx = min(atk_indices, key=lambda idx: attacker.active_slots[idx]['speed'])

            s2['target_slot'] = chosen_idx

    def prepare_turn(self, p1: Unit, p2: Unit):
        """Фаза 1: События начала, перенаправления, инициатива."""
        self.logs = []
        report = []

        # 1. Start Events (Передаем OPPONENT явно, чтобы не крашилось)
        self._trigger_unit_event("on_combat_start", p1, self.log, opponent=p2)
        self._trigger_unit_event("on_combat_start", p2, self.log, opponent=p1)

        if self.logs:
            report.append({"round": "Start", "rolls": "Events", "details": " | ".join(self.logs)})
            self.logs = []

        # 2. Redirects
        ClashSystem.calculate_redirections(p1, p2)
        ClashSystem.calculate_redirections(p2, p1)

        # 3. Collect Actions
        actions = []

        def add_actions(unit, opponent, is_p1_flag):
            for i, slot in enumerate(unit.active_slots):
                if slot.get('card'):
                    # score = скорость + рандом (для разрешения ничьих)
                    score = slot['speed'] + random.random()
                    actions.append({
                        'unit': unit,
                        'opponent': opponent,
                        'slot_idx': i,
                        'slot_data': slot,
                        'is_p1': is_p1_flag,
                        'score': score
                    })

        add_actions(p1, p2, True)
        add_actions(p2, p1, False)

        # Сортировка по скорости (от быстрого к медленному)
        actions.sort(key=lambda x: x['score'], reverse=True)

        return report, actions

    def execute_single_action(self, act, executed_p1, executed_p2):
        """Фаза 2: Выполнение одного действия из очереди."""
        self.logs = []
        u = act['unit']
        opp = act['opponent']
        idx = act['slot_idx']
        is_p1 = act['is_p1']

        # Проверка: если слот уже отыграл (например, был втянут в клеш ранее), пропускаем
        if is_p1:
            if idx in executed_p1: return []
        else:
            if idx in executed_p2: return []

        # Если юнит выбыл (мертв или в стаггере)
        # Примечание: is_staggered() теперь учитывает Ликорис (возвращает False, если активен)
        if u.is_dead() or u.is_staggered(): return []

        target_idx = act['slot_data'].get('target_slot', -1)

        # Если нет цели или цель некорректна
        if target_idx == -1 or target_idx >= len(opp.active_slots):
            return []

        target_slot = opp.active_slots[target_idx]

        # === ОПРЕДЕЛЕНИЕ ТИПА СТЫЧКИ ===
        # Clash происходит, если:
        # 1. Вражеский слот еще не сыграл.
        # 2. Вражеский слот целится в НАШ текущий слот.

        opp_ready = False
        if is_p1:
            if target_idx not in executed_p2: opp_ready = True
        else:
            if target_idx not in executed_p1: opp_ready = True

        is_clash = (target_slot.get('target_slot') == idx) and opp_ready

        # Установка текущих карт для контекста
        u.current_card = act['slot_data']['card']

        battle_logs = []

        if is_clash:
            # === CLASH ===
            # Помечаем оба слота как сыгранные
            if is_p1:
                executed_p1.add(idx)
                executed_p2.add(target_idx)
            else:
                executed_p2.add(idx)
                executed_p1.add(target_idx)

            opp.current_card = target_slot['card']

            # Если враг в стаггере, он не может защищаться -> Односторонняя
            if opp.is_staggered():
                p_label = "P1" if is_p1 else "P2"
                logs = self._resolve_one_sided(u, opp, f"Hit (Stagger)")
                battle_logs.extend(logs)
            else:
                p1_idx = idx if is_p1 else target_idx
                p2_idx = target_idx if is_p1 else idx
                self.log(f"⚔️ Clash: P1[{p1_idx + 1}] vs P2[{p2_idx + 1}]")

                # Запуск механики клеша
                logs = self._resolve_card_clash(u, opp, f"Clash", is_p1_attacker=is_p1)
                battle_logs.extend(logs)

        else:
            # === ONE-SIDED ===
            # Помечаем только свой слот
            if is_p1:
                executed_p1.add(idx)
            else:
                executed_p2.add(idx)

            p_label = "P1" if is_p1 else "P2"

            # Запуск механики односторонней атаки
            # Здесь же внутри сработает проверка на Counter Dice
            logs = self._resolve_one_sided(u, opp, f"{p_label}[{idx + 1}]🏹Hit")
            battle_logs.extend(logs)

        return battle_logs

    def finalize_turn(self, p1: Unit, p2: Unit):
        """Фаза 3: События конца хода."""
        self.logs = []
        report = []

        self._trigger_unit_event("on_combat_end", p1, self.log)
        self._trigger_unit_event("on_combat_end", p2, self.log)

        if self.logs:
            report.append({"round": "End", "rolls": "Events", "details": " | ".join(self.logs)})

        return report

    def resolve_turn(self, p1: Unit, p2: Unit):
        """
        Главный метод, вызываемый из UI.
        Объединяет все фазы.
        """
        full_report = []

        # 1. Start & Init
        init_logs, actions = self.prepare_turn(p1, p2)
        full_report.extend(init_logs)

        executed_p1 = set()
        executed_p2 = set()

        # 2. Action Loop
        for act in actions:
            logs = self.execute_single_action(act, executed_p1, executed_p2)
            full_report.extend(logs)

        # 3. End
        end_logs = self.finalize_turn(p1, p2)
        full_report.extend(end_logs)

        return full_report