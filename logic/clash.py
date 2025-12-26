# logic/clash.py
import random
from core.models import Unit, Dice, DiceType, Card
from logic.context import RollContext
from logic.status_definitions import STATUS_REGISTRY
from logic.card_scripts import SCRIPTS_REGISTRY
from logic.passives import PASSIVE_REGISTRY


class ClashSystem:
    def __init__(self):
        self.logs = []

    def log(self, message):
        self.logs.append(message)

    # ==========================================
    # STATIC: РАСЧЕТ ПЕРЕНАПРАВЛЕНИЙ (ДЛЯ UI И БОЯ)
    # ==========================================
    @staticmethod
    def calculate_redirections(attacker: Unit, defender: Unit):
        """
        Определяет, кто с кем будет драться.
        Правило: Если мы быстрее врага и бьем в его слот, мы можем перехватить его атаку.
        Приоритет:
        1. Слоты с галочкой Aggro.
        2. Самый МЕДЛЕННЫЙ из перехватчиков (чтобы быстрые били One-Sided).
        """
        interceptors = {}

        # 1. Ищем всех кандидатов на перехват
        for i, s1 in enumerate(attacker.active_slots):
            target_idx = s1.get('target_slot', -1)

            # Пропускаем, если цель не валидна
            if target_idx == -1 or target_idx >= len(defender.active_slots):
                continue

            s2 = defender.active_slots[target_idx]

            # Условие перехвата: Наша скорость > Скорости врага
            if s1['speed'] > s2['speed']:
                if target_idx not in interceptors: interceptors[target_idx] = []
                interceptors[target_idx].append(i)

        # 2. Выбираем одного "танка" для каждого слота врага
        for def_idx, atk_indices in interceptors.items():
            s2 = defender.active_slots[def_idx]

            # Фильтруем тех, кто включил AGGRO (ручной приоритет)
            aggro_indices = [idx for idx in atk_indices if attacker.active_slots[idx].get('is_aggro')]

            chosen_idx = None
            if aggro_indices:
                # Если есть Aggro - выбираем самого медленного из них
                chosen_idx = min(aggro_indices, key=lambda idx: attacker.active_slots[idx]['speed'])
            else:
                # Стандарт: выбираем самого медленного из всех (оптимальная тактика)
                chosen_idx = min(atk_indices, key=lambda idx: attacker.active_slots[idx]['speed'])

            # ПРИНУДИТЕЛЬНО меняем цель врага на выбранного танка
            s2['target_slot'] = chosen_idx

    # ==========================================
    # CORE LOOP
    # ==========================================
    def resolve_turn(self, p1: Unit, p2: Unit):
        self.logs = []
        battle_report = []

        # 1. События начала боя
        self._trigger_unit_event("on_combat_start", p1, self.log)
        self._trigger_unit_event("on_combat_start", p2, self.log)

        if self.logs:
            battle_report.append({"round": "Start", "rolls": "Events", "details": " | ".join(self.logs)})
            self.logs = []

        # 2. Применяем логику перенаправления
        ClashSystem.calculate_redirections(p1, p2)
        ClashSystem.calculate_redirections(p2, p1)

        # 3. Собираем все действия в кучу
        actions = []

        def add_actions(unit, opponent, is_p1_flag):
            for i, slot in enumerate(unit.active_slots):
                if slot.get('card'):
                    # Добавляем случайность для разрешения ничьих (Speed Ties)
                    score = slot['speed'] + random.random()
                    actions.append({
                        'unit': unit, 'opponent': opponent,
                        'slot_idx': i, 'slot_data': slot,
                        'is_p1': is_p1_flag, 'score': score, 'speed': slot['speed']
                    })

        add_actions(p1, p2, True)
        add_actions(p2, p1, False)

        # Сортируем: Самые быстрые ходят первыми
        actions.sort(key=lambda x: x['score'], reverse=True)

        executed_p1 = set()
        executed_p2 = set()

        # 4. Выполнение действий
        for act in actions:
            u = act['unit']
            opp = act['opponent']
            idx = act['slot_idx']
            is_p1 = act['is_p1']

            # Проверка: слот уже сыграл?
            if is_p1:
                if idx in executed_p1: continue
            else:
                if idx in executed_p2: continue

            # Проверка: жив ли юнит?
            if u.is_dead() or u.is_staggered(): continue

            target_idx = act['slot_data'].get('target_slot', -1)

            # Пропуск хода (нет цели)
            if target_idx == -1 or target_idx >= len(opp.active_slots):
                continue

            target_slot = opp.active_slots[target_idx]

            # Проверка готовности оппонента к Клешу
            opp_ready = False
            if is_p1:
                if target_idx not in executed_p2: opp_ready = True
            else:
                if target_idx not in executed_p1: opp_ready = True

            # Клеш = Взаимный таргет + Оппонент свободен
            is_clash = (target_slot.get('target_slot') == idx) and opp_ready

            # Устанавливаем текущую карту для расчетов
            u.current_card = act['slot_data']['card']

            if is_clash:
                # --- CLASH ---
                # Помечаем обоих как сыгравших
                if is_p1:
                    executed_p1.add(idx);
                    executed_p2.add(target_idx)
                else:
                    executed_p2.add(idx);
                    executed_p1.add(target_idx)

                opp.current_card = target_slot['card']

                # Если враг в стаггере, он не может защищаться -> One Sided
                if opp.is_staggered():
                    logs = self._resolve_one_sided(u, opp, f"Hit (Stagger)")
                else:
                    # Логирование
                    p1_idx = idx if is_p1 else target_idx
                    p2_idx = target_idx if is_p1 else idx
                    self.log(f"⚔️ Clash: P1[{p1_idx + 1}] vs P2[{p2_idx + 1}]")

                    logs = self._resolve_card_clash(u, opp, f"Clash", is_p1_attacker=is_p1)

                battle_report.extend(logs)

            else:
                # --- ONE-SIDED ---
                # Помечаем только атакующего
                if is_p1:
                    executed_p1.add(idx)
                else:
                    executed_p2.add(idx)

                # В One-Sided оппонент не использует карту для защиты (урон проходит чисто)
                p_label = "P1" if is_p1 else "P2"
                logs = self._resolve_one_sided(u, opp, f"{p_label}[{idx + 1}]🏹Hit")
                battle_report.extend(logs)

        # 5. Конец раунда
        self.logs = []
        self._trigger_unit_event("on_combat_end", p1, self.log)
        self._trigger_unit_event("on_combat_end", p2, self.log)
        if self.logs:
            battle_report.append({"round": "End", "rolls": "Events", "details": " | ".join(self.logs)})

        return battle_report

    # ==========================================
    # RESOLVERS (CLASH & ONE-SIDED)
    # ==========================================
    def _resolve_card_clash(self, attacker: Unit, defender: Unit, round_label: str, is_p1_attacker: bool):
        report = []
        ac = attacker.current_card
        dc = defender.current_card

        self._process_card_self_scripts("on_use", attacker, defender)
        self._process_card_self_scripts("on_use", defender, attacker)

        max_dice = max(len(ac.dice_list), len(dc.dice_list))

        for j in range(max_dice):
            if attacker.is_dead() or defender.is_dead() or attacker.is_staggered(): break

            die_a = ac.dice_list[j] if j < len(ac.dice_list) else None
            die_d = dc.dice_list[j] if j < len(dc.dice_list) else None

            ctx_a = self._create_roll_context(attacker, defender, die_a)
            ctx_d = self._create_roll_context(defender, attacker, die_d)

            val_a = ctx_a.final_value if ctx_a else 0
            val_d = ctx_d.final_value if ctx_d else 0

            # Форматируем лог так, чтобы P1 всегда был слева
            val_p1 = val_a if is_p1_attacker else val_d
            val_p2 = val_d if is_p1_attacker else val_a
            res_str = f"{val_p1} vs {val_p2}"

            detail = ""

            if ctx_a and ctx_d:
                if val_a > val_d:
                    detail = f"{attacker.name} Win!"
                    self._handle_clash_win(ctx_a)
                    self._handle_clash_lose(ctx_d)

                    # Победитель наносит урон/стаггер
                    self._resolve_clash_interaction(ctx_a, ctx_d, val_a - val_d)

                elif val_d > val_a:
                    detail = f"{defender.name} Win!"
                    self._handle_clash_win(ctx_d)
                    self._handle_clash_lose(ctx_a)

                    # Защитник победил и контратакует
                    self._resolve_clash_interaction(ctx_d, ctx_a, val_d - val_a)

                else:
                    detail = "Draw!"
            elif ctx_a:
                detail = "Unanswered"
                self._apply_damage(ctx_a, None, "hp")
            elif ctx_d:
                detail = "Unanswered"
                self._apply_damage(ctx_d, None, "hp")

            round_logs = []
            if ctx_a: round_logs.extend(ctx_a.log)
            if ctx_d: round_logs.extend(ctx_d.log)
            if round_logs: detail += " | " + " ".join(round_logs)

            report.append({"round": f"{round_label} (D{j + 1})", "rolls": res_str, "details": detail})
        return report

    def _resolve_clash_interaction(self, winner_ctx: RollContext, loser_ctx: RollContext, diff: int):
        """Определяет эффект победы в зависимости от типа кубиков"""
        w_type = winner_ctx.dice.dtype
        l_type = loser_ctx.dice.dtype

        # Атаки
        w_is_atk = w_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]
        l_is_atk = l_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]

        # Защита
        w_is_blk = w_type == DiceType.BLOCK
        l_is_blk = l_type == DiceType.BLOCK
        w_is_evd = w_type == DiceType.EVADE

        # 1. Побеждает АТАКА
        if w_is_atk:
            if l_is_atk:
                # Атака vs Атака: Полный урон по HP
                self._apply_damage(winner_ctx, loser_ctx, "hp")

            elif l_is_blk:
                # Атака vs Блок: Урон по HP = (Атака - Блок)
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "hp")

            elif l_is_evd:
                # Атака vs Уклонение: Полный урон по HP
                self._apply_damage(winner_ctx, loser_ctx, "hp")

        # 2. Побеждает БЛОК
        elif w_is_blk:
            if l_is_atk:
                # Блок vs Атака: Парирование -> Stagger урон атакующему
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "stagger")

            elif l_is_blk:
                # Блок vs Блок: Stagger урон проигравшему
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "stagger")

            elif l_is_evd:
                # Блок vs Уклонение: Stagger урон уклоняющемуся
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "stagger")

        # 3. Побеждает УКЛОНЕНИЕ
        elif w_is_evd:
            winner_ctx.log.append("💨 Dodged!")
            # Можно добавить механику восстановления стаггера или реролла

    def _resolve_one_sided(self, source: Unit, target: Unit, round_label: str):
        report = []
        card = source.current_card
        self._process_card_self_scripts("on_use", source, target)

        for j, die in enumerate(card.dice_list):
            if source.is_dead() or target.is_dead() or source.is_staggered(): break

            ctx = self._create_roll_context(source, target, die)
            val = ctx.final_value

            detail = "One-Sided"

            # В односторонней атаке работают только атакующие кубики
            if die.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
                self._apply_damage(ctx, None, "hp")
            else:
                detail = "Defensive Die (Skipped)"

            if ctx.log: detail += " | " + " ".join(ctx.log)
            report.append({"round": f"{round_label} (D{j + 1})", "rolls": f"{val}", "details": detail})

        return report

    # ==========================================
    # HELPERS
    # ==========================================
    def _process_card_self_scripts(self, trigger: str, source: Unit, target: Unit):
        card = source.current_card
        if not card or not card.scripts or trigger not in card.scripts: return
        ctx = RollContext(source=source, target=target, dice=None, final_value=0, log=self.logs)
        for script_data in card.scripts[trigger]:
            script_id = script_data.get("script_id")
            params = script_data.get("params", {})
            if script_id in SCRIPTS_REGISTRY: SCRIPTS_REGISTRY[script_id](ctx, params)

    def _create_roll_context(self, source: Unit, target: Unit, die: Dice) -> RollContext:
        if not die: return None
        roll = random.randint(die.min_val, die.max_val)
        ctx = RollContext(source=source, target=target, dice=die, final_value=roll)

        # Stat bonuses
        if die.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            total = source.modifiers.get("power_attack", 0) + source.modifiers.get("power_medium", 0)
            ctx.modify_power(total, "Stats")
        elif die.dtype == DiceType.BLOCK:
            ctx.modify_power(source.modifiers.get("power_block", 0), "Stats")
        elif die.dtype == DiceType.EVADE:
            ctx.modify_power(source.modifiers.get("power_evade", 0), "Stats")

        # Statuses & Passives
        for status_id, stack in list(source.statuses.items()):
            if status_id in STATUS_REGISTRY: STATUS_REGISTRY[status_id].on_roll(ctx, stack)
        for pid in source.passives + source.talents:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_roll(ctx)

        self._process_card_scripts("on_roll", ctx)
        return ctx

    def _process_card_scripts(self, trigger: str, ctx: RollContext):
        die = ctx.dice
        if not die.scripts or trigger not in die.scripts: return
        for script_data in die.scripts[trigger]:
            script_id = script_data.get("script_id")
            params = script_data.get("params", {})
            if script_id in SCRIPTS_REGISTRY: SCRIPTS_REGISTRY[script_id](ctx, params)

    def _handle_clash_win(self, ctx: RollContext):
        for status_id, stack in list(ctx.source.statuses.items()):
            if status_id in STATUS_REGISTRY: STATUS_REGISTRY[status_id].on_clash_win(ctx, stack)
        for pid in ctx.source.passives + ctx.source.talents:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_clash_win(ctx)
        self._process_card_scripts("on_clash_win", ctx)

    def _handle_clash_lose(self, ctx: RollContext):
        for status_id, stack in list(ctx.source.statuses.items()):
            if status_id in STATUS_REGISTRY: STATUS_REGISTRY[status_id].on_clash_lose(ctx, stack)
        for pid in ctx.source.passives + ctx.source.talents:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_clash_lose(ctx)

    def _trigger_unit_event(self, event_name, unit, *args):
        for status_id, stack in list(unit.statuses.items()):
            if status_id in STATUS_REGISTRY:
                handler = getattr(STATUS_REGISTRY[status_id], event_name, None)
                if handler: handler(unit, *args)
        for pid in unit.passives + unit.talents:
            if pid in PASSIVE_REGISTRY:
                handler = getattr(PASSIVE_REGISTRY[pid], event_name, None)
                if handler: handler(unit, *args)

    # ==========================================
    # DAMAGE CALCULATION
    # ==========================================
    def _deal_direct_damage(self, source_ctx: RollContext, target: Unit, amount: int, dmg_type: str):
        """Наносит чистый урон (после расчетов резистов)"""
        if amount <= 0: return

        if dmg_type == "hp":
            dtype_name = source_ctx.dice.dtype.value.lower()
            res = getattr(target.hp_resists, dtype_name, 1.0)
            final_dmg = int(amount * res)

            barrier = target.get_status("barrier")
            if barrier > 0:
                absorbed = min(barrier, final_dmg)
                target.remove_status("barrier", absorbed)
                final_dmg -= absorbed
                source_ctx.log.append(f"🛡️ Barrier -{absorbed}")

            target.current_hp -= final_dmg
            source_ctx.log.append(f"💥 Hit {final_dmg} HP")

        elif dmg_type == "stagger":
            dtype_name = source_ctx.dice.dtype.value.lower()
            res = getattr(target.stagger_resists, dtype_name, 1.0)
            final_dmg = int(amount * res)

            target.current_stagger -= final_dmg
            source_ctx.log.append(f"😵 Stagger Dmg {final_dmg}")

    def _apply_damage(self, attacker_ctx: RollContext, defender_ctx: RollContext, dmg_type: str = "hp"):
        """Расчет урона с учетом бонусов силы/уязвимости"""
        attacker = attacker_ctx.source
        defender = attacker_ctx.target or attacker_ctx.target

        # On Hit Trigger
        for status_id, stack in list(attacker.statuses.items()):
            if status_id in STATUS_REGISTRY: STATUS_REGISTRY[status_id].on_hit(attacker_ctx, stack)
        for pid in attacker.passives + attacker.talents:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_hit(attacker_ctx)
        self._process_card_scripts("on_hit", attacker_ctx)

        # Base value
        raw_damage = attacker_ctx.final_value

        # Modifiers
        dmg_bonus = attacker.get_status("dmg_up") - attacker.get_status("dmg_down")
        dmg_bonus += attacker.modifiers.get("damage_deal", 0)

        incoming_mod = defender.get_status("fragile") + defender.get_status("vulnerability") - defender.get_status(
            "protection")
        incoming_mod -= defender.modifiers.get("damage_take", 0)

        total_amt = max(0, raw_damage + dmg_bonus + incoming_mod)

        # Apply Main Damage
        self._deal_direct_damage(attacker_ctx, defender, total_amt, dmg_type)

        # Side effect: HP damage always causes some Stagger damage
        if dmg_type == "hp":
            dtype_name = attacker_ctx.dice.dtype.value.lower()
            res_stagger = getattr(defender.stagger_resists, dtype_name, 1.0)
            # Обычно урон по стаггеру от атаки = урону атаки
            stg_dmg = int(total_amt * res_stagger)
            defender.current_stagger -= stg_dmg