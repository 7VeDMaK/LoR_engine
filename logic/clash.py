# logic/clash.py
import random
from logic.clash_flow import ClashFlowMixin


class ClashSystem(ClashFlowMixin):
    """
    Уровень 3: Управление боем (Дирижер).
    Теперь поддерживает пошаговое выполнение.
    """

    def __init__(self):
        self.logs = []

    def log(self, message):
        self.logs.append(message)

    @staticmethod
    def calculate_redirections(attacker, defender):
        # (Код без изменений - см. прошлый ответ или оставьте как есть)
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
            chosen_idx = min(aggro_indices,
                             key=lambda idx: attacker.active_slots[idx]['speed']) if aggro_indices else min(atk_indices,
                                                                                                            key=lambda
                                                                                                                idx:
                                                                                                            attacker.active_slots[
                                                                                                                idx][
                                                                                                                'speed'])
            s2['target_slot'] = chosen_idx

    # === НОВЫЕ МЕТОДЫ ДЛЯ ПОШАГОВОГО БОЯ ===

    def prepare_turn(self, p1, p2):
        """1. События начала боя и сортировка действий"""
        self.logs = []
        init_report = []

        # Start Events
        self._trigger_unit_event("on_combat_start", p1, self.log)
        self._trigger_unit_event("on_combat_start", p2, self.log)
        if self.logs:
            init_report.append({"round": "Start", "details": " | ".join(self.logs)})
            self.logs = []

        # Redirects
        ClashSystem.calculate_redirections(p1, p2)
        ClashSystem.calculate_redirections(p2, p1)

        # Collect Actions
        actions = []

        def add_actions(unit, opponent, is_p1_flag):
            for i, slot in enumerate(unit.active_slots):
                if slot.get('card'):
                    score = slot['speed'] + random.random()
                    actions.append({
                        'unit': unit, 'opponent': opponent,
                        'slot_idx': i, 'slot_data': slot,
                        'is_p1': is_p1_flag, 'score': score, 'speed': slot['speed']
                    })

        add_actions(p1, p2, True)
        add_actions(p2, p1, False)

        # Sort
        actions.sort(key=lambda x: x['score'], reverse=True)

        return init_report, actions

    def execute_single_action(self, action, executed_p1, executed_p2):
        """2. Выполнение одного конкретного действия"""
        battle_logs = []

        u = action['unit']
        opp = action['opponent']
        idx = action['slot_idx']
        slot_data = action['slot_data']
        is_p1 = action['is_p1']

        # Проверка исполнения
        if is_p1:
            if idx in executed_p1: return []
        else:
            if idx in executed_p2: return []

        if u.is_dead() or u.is_staggered(): return []

        target_idx = slot_data.get('target_slot', -1)
        if target_idx == -1 or target_idx >= len(opp.active_slots):
            return []

        target_slot = opp.active_slots[target_idx]

        # Clash Check
        opp_ready = False
        if is_p1:
            if target_idx not in executed_p2: opp_ready = True
        else:
            if target_idx not in executed_p1: opp_ready = True

        is_clash = (target_slot.get('target_slot') == idx) and opp_ready

        u.current_card = slot_data['card']

        if is_clash:
            if is_p1:
                executed_p1.add(idx);
                executed_p2.add(target_idx)
            else:
                executed_p2.add(idx);
                executed_p1.add(target_idx)

            opp.current_card = target_slot['card']

            if opp.is_staggered():
                logs = self._resolve_one_sided(u, opp, f"Hit (Stagger)")
            else:
                logs = self._resolve_card_clash(u, opp, f"Clash", is_p1, slot_a=slot_data, slot_d=target_slot)
            battle_logs.extend(logs)

        else:
            if is_p1:
                executed_p1.add(idx)
            else:
                executed_p2.add(idx)

            p_label = "P1" if is_p1 else "P2"
            logs = self._resolve_one_sided(u, opp, f"{p_label}[{idx + 1}] Hit")
            battle_logs.extend(logs)

        return battle_logs

    def finalize_turn(self, p1, p2):
        """3. События конца боя"""
        self.logs = []
        end_report = []

        self._trigger_unit_event("on_combat_end", p1, self.log)
        self._trigger_unit_event("on_combat_end", p2, self.log)

        if self.logs:
            end_report.append({"round": "End", "details": " | ".join(self.logs)})

        return end_report

    # Старый метод для совместимости (и для Auto-Mode)
    def resolve_turn(self, p1, p2):
        full_report = []

        # 1. Start
        init_logs, actions = self.prepare_turn(p1, p2)
        full_report.extend(init_logs)

        executed_p1 = set()
        executed_p2 = set()

        # 2. Loop
        for act in actions:
            logs = self.execute_single_action(act, executed_p1, executed_p2)
            full_report.extend(logs)

        # 3. End
        end_logs = self.finalize_turn(p1, p2)
        full_report.extend(end_logs)

        return full_report