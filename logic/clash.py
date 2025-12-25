# logic/clash.py
import random
from core.models import Unit, Dice, DiceType
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
    # CORE LOOP
    # ==========================================
    def resolve_card_clash(self, attacker: Unit, defender: Unit,
                           atk_advantage: str = "normal", def_advantage: str = "normal"):
        self.logs = []
        battle_report = []

        # 1. Начало боя (Events)
        self._trigger_unit_event("on_combat_start", attacker, self.log)
        self._trigger_unit_event("on_combat_start", defender, self.log)

        # Скрипты карт (On Use)
        self._process_card_self_scripts("on_use", attacker, defender)
        self._process_card_self_scripts("on_use", defender, attacker)

        self.log(f"Clash Start: {attacker.name} ({atk_advantage}) vs {defender.name} ({def_advantage})")

        if self.logs:
            start_details = " | ".join(self.logs)
            battle_report.append({
                "round": "Start",
                "rolls": "Effects",
                "details": start_details
            })

        # Подготовка карт
        ac = attacker.current_card
        dc = defender.current_card
        if not ac or not dc:
            return [{"round": 0, "rolls": "No Card", "details": "Error"}]

        max_len = max(len(ac.dice_list), len(dc.dice_list))

        for i in range(max_len):
            # Проверка смерти/стаггера
            if attacker.is_dead() or defender.is_dead(): break
            if attacker.is_staggered(): break

            die_a = ac.dice_list[i] if i < len(ac.dice_list) else None
            die_d = dc.dice_list[i] if i < len(dc.dice_list) else None

            # --- ФАЗА БРОСКА (ROLL PHASE) ---
            ctx_a = self._create_roll_context(attacker, defender, die_a, atk_advantage)
            ctx_d = self._create_roll_context(defender, attacker, die_d, def_advantage)

            # Значения для UI
            val_a = ctx_a.final_value if ctx_a else 0
            val_d = ctx_d.final_value if ctx_d else 0

            res_str = f"{attacker.name} [{val_a}] vs [{val_d}] {defender.name}"
            detail = ""

            # --- ФАЗА СРАВНЕНИЯ (CLASH PHASE) ---
            if ctx_a and ctx_d:
                if val_a > val_d:
                    detail = f"{attacker.name} Wins!"
                    self._handle_clash_win(ctx_a)
                    self._handle_clash_lose(ctx_d)
                    if ctx_a.dice.dtype != DiceType.EVADE:
                        self._apply_damage(ctx_a, ctx_d)
                elif val_d > val_a:
                    detail = f"{defender.name} Wins!"
                    self._handle_clash_win(ctx_d)
                    self._handle_clash_lose(ctx_a)
                    if ctx_d.dice.dtype != DiceType.EVADE:
                        self._apply_damage(ctx_d, ctx_a)
                else:
                    detail = "Draw!"
            elif ctx_a:
                detail = "One-Sided Attack"
                self._apply_damage(ctx_a, None)
            elif ctx_d:
                detail = "One-Sided Attack"
                self._apply_damage(ctx_d, None)

            # Запись логов
            round_logs = []
            if ctx_a: round_logs.extend(ctx_a.log)
            if ctx_d: round_logs.extend(ctx_d.log)

            if round_logs:
                if detail:
                    detail += " | " + " ".join(round_logs)
                else:
                    detail = " ".join(round_logs)

            battle_report.append({"round": i + 1, "rolls": res_str, "details": detail})

        # 3. Конец боя
        self._trigger_unit_event("on_combat_end", attacker, self.log)
        self._trigger_unit_event("on_combat_end", defender, self.log)

        return battle_report

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

    def _create_roll_context(self, source: Unit, target: Unit, die: Dice, advantage: str) -> RollContext:
        if not die: return None

        roll = random.randint(die.min_val, die.max_val)
        if advantage == "advantage":
            roll = max(roll, random.randint(die.min_val, die.max_val))
        elif advantage == "disadvantage":
            roll = min(roll, random.randint(die.min_val, die.max_val))
        elif advantage == "impossible":
            roll = 0

        ctx = RollContext(source=source, target=target, dice=die, final_value=roll)

        # === 0. ПРИМЕНЯЕМ СТАТЫ ПРОФИЛЯ (Unit Modifiers) ===
        # source.modifiers заполняется методом unit.recalculate_stats()

        # Атакующие кубики (Slash, Pierce, Blunt)
        if die.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            # Сила (Power Attack)
            str_bonus = source.modifiers.get("power_attack", 0)
            # Навык Оружия (пока берем Medium для всех, как просили)
            wep_bonus = source.modifiers.get("power_medium", 0)

            total_stat_bonus = str_bonus + wep_bonus
            ctx.modify_power(total_stat_bonus, "Stats")

        # Защитные кубики
        elif die.dtype == DiceType.BLOCK:
            blk_bonus = source.modifiers.get("power_block", 0)
            ctx.modify_power(blk_bonus, "Stats")

        elif die.dtype == DiceType.EVADE:
            evd_bonus = source.modifiers.get("power_evade", 0)
            ctx.modify_power(evd_bonus, "Stats")

        # === 1. Статусы (Strength, Paralysis) ===
        for status_id, stack in list(source.statuses.items()):
            if status_id in STATUS_REGISTRY:
                STATUS_REGISTRY[status_id].on_roll(ctx, stack)

        # === 2. Пассивки ===
        for pid in source.passives + source.talents:
            if pid in PASSIVE_REGISTRY:
                PASSIVE_REGISTRY[pid].on_roll(ctx)

        # === 3. Скрипты карты ===
        self._process_card_scripts("on_roll", ctx)
        return ctx

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

    def _apply_damage(self, attacker_ctx: RollContext, defender_ctx: RollContext):
        attacker = attacker_ctx.source
        defender = attacker_ctx.target or attacker_ctx.target

        # On Hit
        for status_id, stack in list(attacker.statuses.items()):
            if status_id in STATUS_REGISTRY: STATUS_REGISTRY[status_id].on_hit(attacker_ctx, stack)
        for pid in attacker.passives + attacker.talents:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_hit(attacker_ctx)
        self._process_card_scripts("on_hit", attacker_ctx)

        raw_damage = attacker_ctx.final_value
        dmg_bonus = attacker.get_status("dmg_up") - attacker.get_status("dmg_down")
        # Бонус к урону от навыков ("damage_deal")
        dmg_bonus += attacker.modifiers.get("damage_deal", 0)

        raw_damage += dmg_bonus

        dtype_name = attacker_ctx.dice.dtype.value.lower()
        res_hp = getattr(defender.hp_resists, dtype_name, 1.0)
        res_stagger = getattr(defender.stagger_resists, dtype_name, 1.0)

        incoming_mod = defender.get_status("fragile") + defender.get_status("vulnerability") - defender.get_status(
            "protection")
        # Снижение урона от навыков (Tough Skin)
        incoming_mod -= defender.modifiers.get("damage_take", 0)

        final_hp_dmg = int(raw_damage * res_hp) + incoming_mod
        final_hp_dmg = max(0, final_hp_dmg)
        final_stg_dmg = int(raw_damage * res_stagger)

        barrier = defender.get_status("barrier")
        if barrier > 0:
            absorbed = min(barrier, final_hp_dmg)
            defender.remove_status("barrier", absorbed)
            final_hp_dmg -= absorbed
            attacker_ctx.log.append(f"🛡️ Barrier -{absorbed}")

        defender.current_hp -= final_hp_dmg
        defender.current_stagger -= final_stg_dmg
        attacker_ctx.log.append(f"💥 Hit {final_hp_dmg} HP")

    def _process_card_scripts(self, trigger: str, ctx: RollContext):
        die = ctx.dice
        if not die.scripts or trigger not in die.scripts: return
        for script_data in die.scripts[trigger]:
            script_id = script_data.get("script_id")
            params = script_data.get("params", {})
            if script_id in SCRIPTS_REGISTRY: SCRIPTS_REGISTRY[script_id](ctx, params)