import random
from core.models import Dice, DiceType
from logic.context import RollContext
from logic.status_definitions import STATUS_REGISTRY
from logic.card_scripts import SCRIPTS_REGISTRY
from logic.passives import PASSIVE_REGISTRY
from logic.talents import TALENT_REGISTRY


class ClashMechanicsMixin:
    """
    Уровень 1: Низкоуровневая механика.
    Содержит методы бросков и нанесения урона.
    """

    def _process_card_scripts(self, trigger: str, ctx: RollContext):
        die = ctx.dice
        if not die or not die.scripts or trigger not in die.scripts: return
        for script_data in die.scripts[trigger]:
            script_id = script_data.get("script_id")
            params = script_data.get("params", {})
            if script_id in SCRIPTS_REGISTRY: SCRIPTS_REGISTRY[script_id](ctx, params)

    def _process_card_self_scripts(self, trigger: str, source, target, custom_log_list=None):
        card = source.current_card
        if not card or not card.scripts or trigger not in card.scripts: return

        # Если нам дали список, пишем в него. Если нет — используем self.logs
        target_log = custom_log_list if custom_log_list is not None else self.logs

        ctx = RollContext(source=source, target=target, dice=None, final_value=0, log=target_log)

        for script_data in card.scripts[trigger]:
            script_id = script_data.get("script_id")
            params = script_data.get("params", {})
            if script_id in SCRIPTS_REGISTRY:
                SCRIPTS_REGISTRY[script_id](ctx, params)

    def _create_roll_context(self, source, target, die: Dice, is_disadvantage: bool = False) -> RollContext:
        if not die: return None
        if is_disadvantage:
            r1 = random.randint(die.min_val, die.max_val)
            r2 = random.randint(die.min_val, die.max_val)
            roll = min(r1, r2)
            ctx = RollContext(source=source, target=target, dice=die, final_value=roll, is_disadvantage=True)
            ctx.log.append(f"📉 **Помеха!** (Speed): {r1}, {r2} -> **{roll}**")
        else:
            roll = random.randint(die.min_val, die.max_val)
            ctx = RollContext(source=source, target=target, dice=die, final_value=roll, is_disadvantage=False)
            ctx.log.append(f"🎲 Roll [{die.min_val}-{die.max_val}]: **{roll}**")

        mods = source.modifiers
        if die.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            p_atk = mods.get("power_attack", 0)
            if p_atk: ctx.modify_power(p_atk, "Сила")
            p_skill = mods.get("power_medium", 0)
            if p_skill: ctx.modify_power(p_skill, "Навык")
        elif die.dtype == DiceType.BLOCK:
            p_blk = mods.get("power_block", 0)
            if p_blk: ctx.modify_power(p_blk, "Стойкость")
        elif die.dtype == DiceType.EVADE:
            p_evd = mods.get("power_evade", 0)
            if p_evd: ctx.modify_power(p_evd, "Ловкость")

        # === РУЧНОЙ ПЕРЕБОР ДЛЯ ON_ROLL (Чтобы не ломать сигнатуры) ===
        for status_id, stack in list(source.statuses.items()):
            if status_id in STATUS_REGISTRY: STATUS_REGISTRY[status_id].on_roll(ctx, stack)

        for pid in source.passives:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_roll(ctx)

        for pid in source.talents:
            if pid in TALENT_REGISTRY: TALENT_REGISTRY[pid].on_roll(ctx)

        self._process_card_scripts("on_roll", ctx)
        return ctx

    def _handle_clash_win(self, ctx: RollContext):
        for status_id, stack in list(ctx.source.statuses.items()):
            if status_id in STATUS_REGISTRY: STATUS_REGISTRY[status_id].on_clash_win(ctx, stack)
        for pid in ctx.source.passives:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_clash_win(ctx)
        for pid in ctx.source.talents:
            if pid in TALENT_REGISTRY: TALENT_REGISTRY[pid].on_clash_win(ctx)
        self._process_card_scripts("on_clash_win", ctx)

    def _handle_clash_lose(self, ctx: RollContext):
        for status_id, stack in list(ctx.source.statuses.items()):
            if status_id in STATUS_REGISTRY: STATUS_REGISTRY[status_id].on_clash_lose(ctx, stack)
        for pid in ctx.source.passives:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_clash_lose(ctx)
        for pid in ctx.source.talents:
            if pid in TALENT_REGISTRY: TALENT_REGISTRY[pid].on_clash_lose(ctx)
        self._process_card_scripts("on_clash_lose", ctx)

    # === УНИВЕРСАЛЬНЫЙ ТРИГГЕР (Используется для on_take_damage, on_combat_start) ===
    def _trigger_unit_event(self, event_name, unit, *args, **kwargs):
        for status_id, stack in list(unit.statuses.items()):
            if status_id in STATUS_REGISTRY:
                handler = getattr(STATUS_REGISTRY[status_id], event_name, None)
                # Внимание: Статусы могут не поддерживать (unit, ...), если это не start/end/damage события.
                # Но для on_take_damage это подходит.
                if handler: handler(unit, *args, **kwargs)

        for pid in unit.passives:
            if pid in PASSIVE_REGISTRY:
                handler = getattr(PASSIVE_REGISTRY[pid], event_name, None)
                if handler: handler(unit, *args, **kwargs)

        for pid in unit.talents:
            if pid in TALENT_REGISTRY:
                handler = getattr(TALENT_REGISTRY[pid], event_name, None)
                if handler: handler(unit, *args, **kwargs)

    # === НАНЕСЕНИЕ УРОНА ===
    def _deal_direct_damage(self, source_ctx: RollContext, target, amount: int, dmg_type: str):
        if amount <= 0: return
        if target.get_status("red_lycoris") > 0:
            source_ctx.log.append(f"🚫 {target.name} Immune (Lycoris)")
            return

        final_dmg = 0

        if dmg_type == "hp":
            dtype_name = source_ctx.dice.dtype.value.lower()
            res = getattr(target.hp_resists, dtype_name, 1.0)
            is_stag_hit = False
            if target.is_staggered():
                res *= 2.0
                is_stag_hit = True

            final_dmg = int(amount * res)
            barrier = target.get_status("barrier")
            if barrier > 0:
                absorbed = min(barrier, final_dmg)
                target.remove_status("barrier", absorbed)
                final_dmg -= absorbed
                source_ctx.log.append(f"🛡️ Барьер поглотил {absorbed}")

            target.current_hp -= final_dmg
            msg = f"💥 **{final_dmg}** урона по {target.name}"
            if is_stag_hit: msg += " (Stagger x2!)"
            source_ctx.log.append(msg)

        elif dmg_type == "stagger":
            dtype_name = source_ctx.dice.dtype.value.lower()
            # Используем HP резисты для стаггера (по вашему запросу)
            res = getattr(target.hp_resists, dtype_name, 1.0)

            final_dmg = int(amount * res)
            target.current_stagger -= final_dmg

            resist_msg = ""
            if res != 1.0: resist_msg = f" (Res x{res:.1f})"

            source_ctx.log.append(f"😵 **{final_dmg}** Stagger урона{resist_msg} по {target.name}")

        # === ТРИГГЕР ПОЛУЧЕНИЯ УРОНА (ВНЕ IF/ELSE) ===
        if final_dmg > 0:
            log_wrapper = lambda msg: source_ctx.log.append(msg)
            # Передаем: (unit, amount, type, log_func)
            self._trigger_unit_event("on_take_damage", target, final_dmg, dmg_type, log_func=log_wrapper)

    def _apply_damage(self, attacker_ctx: RollContext, defender_ctx: RollContext, dmg_type: str = "hp"):
        """Стандартный расчет урона от атаки."""
        attacker = attacker_ctx.source
        defender = attacker_ctx.target or attacker_ctx.target

        if defender.get_status("red_lycoris") > 0:
            attacker_ctx.log.append(f"🚫 {defender.name} Immune (Lycoris)")
            return

        # === РУЧНОЙ ПЕРЕБОР ON_HIT (Чтобы починить TypeError) ===
        for status_id, stack in list(attacker.statuses.items()):
            if status_id in STATUS_REGISTRY: STATUS_REGISTRY[status_id].on_hit(attacker_ctx, stack)

        for pid in attacker.passives:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_hit(attacker_ctx)

        for pid in attacker.talents:
            if pid in TALENT_REGISTRY: TALENT_REGISTRY[pid].on_hit(attacker_ctx)

        self._process_card_scripts("on_hit", attacker_ctx)

        # === РАСЧЕТ ===
        raw_damage = attacker_ctx.final_value

        dmg_bonus_status = attacker.get_status("dmg_up") - attacker.get_status("dmg_down")
        dmg_bonus_mods = attacker.modifiers.get("damage_deal", 0)

        incoming_mod = defender.get_status("fragile") + defender.get_status("vulnerability") - defender.get_status(
            "protection")
        incoming_mod_stats = defender.modifiers.get("damage_take", 0)
        incoming_total = incoming_mod - incoming_mod_stats

        total_base = max(0, raw_damage + dmg_bonus_status + dmg_bonus_mods + incoming_total)

        # Множители (Крит)
        final_amt = total_base
        if attacker_ctx.damage_multiplier != 1.0:
            final_amt = int(final_amt * attacker_ctx.damage_multiplier)

        # Лог формула
        math_parts = [f"{raw_damage}"]
        if dmg_bonus_status + dmg_bonus_mods != 0:
            math_parts.append(f"{dmg_bonus_status + dmg_bonus_mods:+} (Atk)")
        if incoming_total != 0:
            math_parts.append(f"{incoming_total:+} (Def)")

        formula = "".join(math_parts)
        if attacker_ctx.damage_multiplier != 1.0:
            formula = f"({formula}) x{attacker_ctx.damage_multiplier} (Crit)"

        dtype_name = attacker_ctx.dice.dtype.value.lower()
        resist_val = getattr(defender.hp_resists, dtype_name, 1.0)
        if resist_val != 1.0:
            formula += f" x{resist_val} (Res)"

        # Наносим урон
        if dmg_type == "hp":
            self._deal_direct_damage(attacker_ctx, defender, final_amt, dmg_type)
            attacker_ctx.log[-1] += f" [{formula}]"

        elif dmg_type == "stagger":
            self._deal_direct_damage(attacker_ctx, defender, final_amt, dmg_type)

        if dmg_type == "hp" and not defender.is_staggered():
            if defender.get_status("red_lycoris") <= 0:
                res_stagger = getattr(defender.stagger_resists, dtype_name, 1.0)
                stg_dmg = int(final_amt * res_stagger)
                defender.current_stagger -= stg_dmg