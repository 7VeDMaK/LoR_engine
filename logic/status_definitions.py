# logic/status_definitions.py
from logic.context import RollContext
from core.models import DiceType


class StatusEffect:
    id = "base"

    def on_use(self, unit, card, log_func): pass

    def on_combat_start(self, unit, log_func): pass

    def on_combat_end(self, unit, log_func): pass

    def on_roll(self, ctx: RollContext, stack: int): pass

    def on_clash_win(self, ctx: RollContext, stack: int): pass

    def on_clash_lose(self, ctx: RollContext, stack: int): pass

    def on_hit(self, ctx: RollContext, stack: int): pass

    def on_turn_end(self, unit, stack) -> list[str]:
        # Возвращаем только логи (например, урон).
        # Само удаление статуса делает StatusManager.
        return []


class StrengthStatus(StatusEffect):
    id = "strength"

    def on_roll(self, ctx: RollContext, stack: int):
        if ctx.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            ctx.modify_power(stack, "Strength")

    def on_turn_end(self, unit, stack):
        return []


class BleedStatus(StatusEffect):
    id = "bleed"

    def on_roll(self, ctx: RollContext, stack: int):
        if ctx.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            dmg = stack
            ctx.source.current_hp -= dmg

            # Логика: при срабатывании стаки уполовиниваются
            new_stack = stack // 2
            if new_stack > 0:
                ctx.source.statuses["bleed"] = new_stack
            else:
                ctx.source.remove_status("bleed")  # Тут удаляем, т.к. стаки кончились

            ctx.log.append(f"🩸 Bleed: {ctx.source.name} takes {dmg} dmg")

    def on_turn_end(self, unit, stack):
        # Здесь ничего не делаем, менеджер сам удалит если duration истек (1 ход по умолчанию)
        return ["Bleed expired"]


class ParalysisStatus(StatusEffect):
    id = "paralysis"

    def on_roll(self, ctx: RollContext, stack: int):
        ctx.modify_power(-3, "Paralysis")
        ctx.source.remove_status("paralysis", 1)


STATUS_REGISTRY = {
    "strength": StrengthStatus(),
    "bleed": BleedStatus(),
    "paralysis": ParalysisStatus(),
}