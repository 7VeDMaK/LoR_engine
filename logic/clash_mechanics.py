# logic/clash_mechanics.py
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
    """

    def _process_card_scripts(self, trigger: str, ctx: RollContext):
        die = ctx.dice
        if not die.scripts or trigger not in die.scripts: return
        for script_data in die.scripts[trigger]:
            script_id = script_data.get("script_id")
            params = script_data.get("params", {})
            if script_id in SCRIPTS_REGISTRY: SCRIPTS_REGISTRY[script_id](ctx, params)

    def _process_card_self_scripts(self, trigger: str, source, target):
        card = source.current_card
        if not card or not card.scripts or trigger not in card.scripts: return
        ctx = RollContext(source=source, target=target, dice=None, final_value=0, log=self.logs)
        for script_data in card.scripts[trigger]:
            script_id = script_data.get("script_id")
            params = script_data.get("params", {})
            if script_id in SCRIPTS_REGISTRY: SCRIPTS_REGISTRY[script_id](ctx, params)

    def _create_roll_context(self, source, target, die: Dice) -> RollContext:
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

        # Statuses
        for status_id, stack in list(source.statuses.items()):
            if status_id in STATUS_REGISTRY: STATUS_REGISTRY[status_id].on_roll(ctx, stack)

        # Passives
        for pid in source.passives:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_roll(ctx)

        # Talents (NEW)
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

    def _trigger_unit_event(self, event_name, unit, *args):
        # Statuses
        for status_id, stack in list(unit.statuses.items()):
            if status_id in STATUS_REGISTRY:
                handler = getattr(STATUS_REGISTRY[status_id], event_name, None)
                if handler: handler(unit, *args)

        # Passives
        for pid in unit.passives:
            if pid in PASSIVE_REGISTRY:
                handler = getattr(PASSIVE_REGISTRY[pid], event_name, None)
                if handler: handler(unit, *args)

        # Talents (NEW)
        for pid in unit.talents:
            if pid in TALENT_REGISTRY:
                handler = getattr(TALENT_REGISTRY[pid], event_name, None)
                if handler: handler(unit, *args)

    # === DAMAGE CALCULATIONS ===

    def _deal_direct_damage(self, source_ctx: RollContext, target, amount: int, dmg_type: str):
        """Наносит урон (HP или Stagger)."""
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
                source_ctx.log.append(f"🛡️ Barrier -{absorbed}")

            target.current_hp -= final_dmg

            hit_msg = f"💥 Hit {final_dmg} HP"
            if is_stag_hit:
                hit_msg += " (Stagger x2!)"
            source_ctx.log.append(hit_msg)

        elif dmg_type == "stagger":
            dtype_name = source_ctx.dice.dtype.value.lower()
            res = getattr(target.stagger_resists, dtype_name, 1.0)
            final_dmg = int(amount * res)

            target.current_stagger -= final_dmg
            source_ctx.log.append(f"😵 Stagger Dmg {final_dmg}")

    def _apply_damage(self, attacker_ctx: RollContext, defender_ctx: RollContext, dmg_type: str = "hp"):
        """Стандартный расчет урона от атаки."""
        attacker = attacker_ctx.source
        defender = attacker_ctx.target or attacker_ctx.target

        # On Hit Events
        for status_id, stack in list(attacker.statuses.items()):
            if status_id in STATUS_REGISTRY: STATUS_REGISTRY[status_id].on_hit(attacker_ctx, stack)

        for pid in attacker.passives:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_hit(attacker_ctx)
        for pid in attacker.talents:
            if pid in TALENT_REGISTRY: TALENT_REGISTRY[pid].on_hit(attacker_ctx)

        self._process_card_scripts("on_hit", attacker_ctx)

        raw_damage = attacker_ctx.final_value

        # Modifiers
        dmg_bonus = attacker.get_status("dmg_up") - attacker.get_status("dmg_down")
        dmg_bonus += attacker.modifiers.get("damage_deal", 0)

        incoming_mod = defender.get_status("fragile") + defender.get_status("vulnerability") - defender.get_status(
            "protection")
        incoming_mod -= defender.modifiers.get("damage_take", 0)

        total_amt = max(0, raw_damage + dmg_bonus + incoming_mod)

        # === КРИТИЧЕСКИЙ УДАР (МНОЖИТЕЛЬ) ===
        if attacker_ctx.damage_multiplier != 1.0:
            total_amt = int(total_amt * attacker_ctx.damage_multiplier)

        self._deal_direct_damage(attacker_ctx, defender, total_amt, dmg_type)

        if dmg_type == "hp" and not defender.is_staggered():
            dtype_name = attacker_ctx.dice.dtype.value.lower()
            res_stagger = getattr(defender.stagger_resists, dtype_name, 1.0)
            stg_dmg = int(total_amt * res_stagger)
            defender.current_stagger -= stg_dmg