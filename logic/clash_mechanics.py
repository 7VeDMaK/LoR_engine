import random
from core.models import Dice, DiceType
from logic.context import RollContext
from logic.status_definitions import STATUS_REGISTRY
from logic.card_scripts import SCRIPTS_REGISTRY
from logic.passives.__init__ import PASSIVE_REGISTRY
from logic.talents import TALENT_REGISTRY


class ClashMechanicsMixin:
    """
    Уровень 1: Низкоуровневая механика.
    Содержит методы бросков (включая Помеху) и нанесения урона.
    """

    def _dispatch_event(self, event_name: str, context: RollContext, *args):
        unit = context.source
        for status_id, stack in list(unit.statuses.items()):
            if status_id in STATUS_REGISTRY:
                handler = getattr(STATUS_REGISTRY[status_id], event_name, None)
                if handler: handler(context, stack, *args)
        for pid in unit.passives:
            if pid in PASSIVE_REGISTRY:
                handler = getattr(PASSIVE_REGISTRY[pid], event_name, None)
                if handler: handler(context, *args)
        for pid in unit.talents:
            if pid in TALENT_REGISTRY:
                handler = getattr(TALENT_REGISTRY[pid], event_name, None)
                if handler: handler(context, *args)
        self._process_card_scripts(event_name, context)

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

        # Если нам дали список, пишем в него. Если нет — используем self.logs (как раньше)
        target_log = custom_log_list if custom_log_list is not None else self.logs

        # Создаем контекст с правильным логом
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

        self._dispatch_event("on_roll", ctx)
        return ctx

    def _handle_clash_win(self, ctx: RollContext):
        self._dispatch_event("on_clash_win", ctx)

    def _handle_clash_lose(self, ctx: RollContext):
        self._dispatch_event("on_clash_lose", ctx)

    def _trigger_unit_event(self, event_name, unit, *args):
        for status_id, stack in list(unit.statuses.items()):
            if status_id in STATUS_REGISTRY:
                handler = getattr(STATUS_REGISTRY[status_id], event_name, None)
                if handler: handler(unit, *args)
        for pid in unit.passives:
            if pid in PASSIVE_REGISTRY:
                handler = getattr(PASSIVE_REGISTRY[pid], event_name, None)
                if handler: handler(unit, *args)
        for pid in unit.talents:
            if pid in TALENT_REGISTRY:
                handler = getattr(TALENT_REGISTRY[pid], event_name, None)
                if handler: handler(unit, *args)

    def _deal_direct_damage(self, source_ctx: RollContext, target, amount: int, dmg_type: str):
        if amount <= 0: return

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

            # === ИЗМЕНЕНИЕ: Используем HP_RESISTS для стаггер-урона ===
            # Раньше было: res = getattr(target.stagger_resists, dtype_name, 1.0)
            res = getattr(target.hp_resists, dtype_name, 1.0)

            final_dmg = int(amount * res)
            target.current_stagger -= final_dmg

            # Добавляем инфо о резистах в лог, если они отличаются от 1.0
            resist_msg = ""
            if res != 1.0: resist_msg = f" (Res x{res:.1f})"

            source_ctx.log.append(f"😵 **{final_dmg}** Stagger урона{resist_msg} по {target.name}")

    def _apply_damage(self, attacker_ctx: RollContext, defender_ctx: RollContext, dmg_type: str = "hp"):
        attacker = attacker_ctx.source
        defender = attacker_ctx.target or attacker_ctx.target

        self._dispatch_event("on_hit", attacker_ctx)

        raw_damage = attacker_ctx.final_value

        dmg_bonus = attacker.get_status("dmg_up") - attacker.get_status("dmg_down")
        dmg_bonus += attacker.modifiers.get("damage_deal", 0)

        incoming_mod = defender.get_status("fragile") + defender.get_status("vulnerability") - defender.get_status(
            "protection")
        incoming_mod -= defender.modifiers.get("damage_take", 0)

        total_amt = max(0, raw_damage + dmg_bonus + incoming_mod)

        # Процентные модификаторы (Дым и т.д.)
        pct_modifier = 0.0
        for status_id, stack in defender.statuses.items():
            if status_id in STATUS_REGISTRY:
                modifier_func = getattr(STATUS_REGISTRY[status_id], "get_damage_modifier", None)
                if modifier_func:
                    pct_modifier += modifier_func(defender, stack)

        if pct_modifier != 0.0:
            original = total_amt
            total_amt = int(total_amt * (1.0 + pct_modifier))
            pct_str = f"{pct_modifier * 100:+.0f}%"
            attacker_ctx.log.append(f"🌫️ Mods: {original} -> **{total_amt}** ({pct_str})")

        if attacker_ctx.damage_multiplier != 1.0:
            total_amt = int(total_amt * attacker_ctx.damage_multiplier)
            attacker_ctx.log.append(f"⚡ Крит x{attacker_ctx.damage_multiplier}!")

        self._deal_direct_damage(attacker_ctx, defender, total_amt, dmg_type)

        if dmg_type == "hp" and not defender.is_staggered():
            dtype_name = attacker_ctx.dice.dtype.value.lower()
            # Stagger урон от HP атаки тоже считаем через hp_resists, если нужно единообразие?
            # В оригинале HP атака наносит доп. Stagger урон.
            # Оставим тут пока stagger_resists или заменим на hp_resists, если ты хочешь ПОЛНОЕ соответствие.
            # Судя по запросу "stagger damage dealt... same as normal resists", заменим и тут.
            res_stagger = getattr(defender.hp_resists, dtype_name, 1.0)

            stg_dmg = int(total_amt * res_stagger)
            defender.current_stagger -= stg_dmg