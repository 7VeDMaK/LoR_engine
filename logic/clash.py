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
            target_idx = s1.get('target_slot', -1)
            if target_idx != -1 and target_idx < len(defender.active_slots):
                s2 = defender.active_slots[target_idx]
                if s1['speed'] > s2['speed']:
                    if target_idx not in interceptors: interceptors[target_idx] = []
                    interceptors[target_idx].append(i)

        for def_idx, atk_indices in interceptors.items():
            s2 = defender.active_slots[def_idx]
            aggro_indices = [idx for idx in atk_indices if attacker.active_slots[idx].get('is_aggro')]

            chosen_idx = None
            if aggro_indices:
                # Если есть Aggro, берем самого медленного из них
                chosen_idx = min(aggro_indices, key=lambda idx: attacker.active_slots[idx]['speed'])
            else:
                # Иначе берем самого медленного из всех (стандарт)
                chosen_idx = min(atk_indices, key=lambda idx: attacker.active_slots[idx]['speed'])

            s2['target_slot'] = chosen_idx

    def resolve_turn(self, p1: Unit, p2: Unit):
        self.logs = []
        battle_report = []

        self._trigger_unit_event("on_combat_start", p1, self.log)
        self._trigger_unit_event("on_combat_start", p2, self.log)
        if self.logs:
            battle_report.append({"round": "Start", "rolls": "Events", "details": " | ".join(self.logs)})
            self.logs = []

        ClashSystem.calculate_redirections(p1, p2)
        ClashSystem.calculate_redirections(p2, p1)

        actions = []
        def add_actions(unit, opponent, is_p1_flag):
            for i, slot in enumerate(unit.active_slots):
                if slot.get('card'):
                    score = slot['speed'] + random.random()
                    actions.append({
                        'unit': unit, 'opponent': opponent,
                        'slot_idx': i, 'slot_data': slot,
                        'is_p1': is_p1_flag, 'score': score
                    })

        add_actions(p1, p2, True)
        add_actions(p2, p1, False)
        actions.sort(key=lambda x: x['score'], reverse=True)

        executed_p1 = set()
        executed_p2 = set()

        for act in actions:
            u = act['unit']
            opp = act['opponent']
            idx = act['slot_idx']
            is_p1 = act['is_p1']
            slot_data = act['slot_data'] # Наш слот

            if is_p1:
                if idx in executed_p1: continue
            else:
                if idx in executed_p2: continue

            if u.is_dead() or u.is_staggered(): continue

            target_idx = slot_data.get('target_slot', -1)
            if target_idx == -1 or target_idx >= len(opp.active_slots): continue

            target_slot = opp.active_slots[target_idx] # Слот врага

            opp_ready = False
            if is_p1:
                if target_idx not in executed_p2: opp_ready = True
            else:
                if target_idx not in executed_p1: opp_ready = True

            is_clash = (target_slot.get('target_slot') == idx) and opp_ready

            u.current_card = slot_data['card']

            if is_clash:
                if is_p1:
                    executed_p1.add(idx); executed_p2.add(target_idx)
                else:
                    executed_p2.add(idx); executed_p1.add(target_idx)

                opp.current_card = target_slot['card']

                if opp.is_staggered():
                    logs = self._resolve_one_sided(u, opp, f"Hit (Stagger)")
                else:
                    p1_idx = idx if is_p1 else target_idx
                    p2_idx = target_idx if is_p1 else idx
                    self.log(f"⚔️ Clash: P1[{p1_idx + 1}] vs P2[{p2_idx + 1}]")

                    # ПЕРЕДАЕМ ОБЪЕКТЫ СЛОТОВ ЦЕЛИКОМ (с флагами force_clash)
                    logs = self._resolve_card_clash(u, opp, f"Clash", is_p1_attacker=is_p1, slot_a=slot_data, slot_d=target_slot)

                battle_report.extend(logs)
            else:
                if is_p1: executed_p1.add(idx)
                else: executed_p2.add(idx)

                p_label = "P1" if is_p1 else "P2"
                logs = self._resolve_one_sided(u, opp, f"{p_label}[{idx + 1}]🏹Hit")
                battle_report.extend(logs)

        self.logs = []
        self._trigger_unit_event("on_combat_end", p1, self.log)
        self._trigger_unit_event("on_combat_end", p2, self.log)
        if self.logs:
            battle_report.append({"round": "End", "rolls": "Events", "details": " | ".join(self.logs)})

        return battle_report