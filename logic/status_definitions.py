# logic/status_definitions.py
from logic.context import RollContext
from core.models import DiceType


class StatusEffect:
    id = "base"

    # Базовые методы-заглушки
    def on_use(self, unit, card, log_func): pass

    def on_combat_start(self, unit, log_func): pass

    def on_combat_end(self, unit, log_func): pass

    def on_roll(self, ctx: RollContext, stack: int): pass

    def on_clash_win(self, ctx: RollContext, stack: int): pass

    def on_clash_lose(self, ctx: RollContext, stack: int): pass

    def on_hit(self, ctx: RollContext, stack: int): pass

    def on_turn_end(self, unit, stack) -> list[str]:
        return []


class StrengthStatus(StatusEffect):
    id = "strength"

    def on_roll(self, ctx: RollContext, stack: int):
        if ctx.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            ctx.modify_power(stack, "Strength")

    def on_turn_end(self, unit, stack):
        # Менеджер сам удалит истекшие таймеры
        return []


class BleedStatus(StatusEffect):
    id = "bleed"

    def on_roll(self, ctx: RollContext, stack: int):
        if ctx.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            dmg = stack
            ctx.source.current_hp -= dmg

            # ИСПРАВЛЕНИЕ: Используем remove_status для корректного списания
            remove_amt = stack // 2
            ctx.source.remove_status("bleed", remove_amt)

            ctx.log.append(f"🩸 Bleed: {ctx.source.name} takes {dmg} dmg")

    def on_turn_end(self, unit, stack):
        return []  # Таймер обрабатывается менеджером


class ParalysisStatus(StatusEffect):
    id = "paralysis"

    def on_roll(self, ctx: RollContext, stack: int):
        ctx.modify_power(-3, "Paralysis")
        # Списываем 1 стак паралича
        ctx.source.remove_status("paralysis", 1)


STATUS_REGISTRY = {
    "strength": StrengthStatus(),
    "bleed": BleedStatus(),
    "paralysis": ParalysisStatus(),
}