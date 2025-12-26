import random
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

    def on_turn_end(self, unit, stack) -> list[str]: return []


class StrengthStatus(StatusEffect):
    id = "strength"

    def on_roll(self, ctx: RollContext, stack: int):
        if ctx.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            ctx.modify_power(stack, "Strength")


class BleedStatus(StatusEffect):
    id = "bleed"

    def on_roll(self, ctx: RollContext, stack: int):
        if ctx.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            dmg = stack
            ctx.source.current_hp -= dmg
            remove_amt = stack // 2
            ctx.source.remove_status("bleed", remove_amt)
            ctx.log.append(f"🩸 Bleed: {ctx.source.name} takes {dmg} dmg")


class ParalysisStatus(StatusEffect):
    id = "paralysis"

    def on_roll(self, ctx: RollContext, stack: int):
        ctx.modify_power(-3, "Paralysis")
        ctx.source.remove_status("paralysis", 1)


# === НОВЫЙ СТАТУС: САМООБЛАДАНИЕ (Self-Control) ===
class SelfControlStatus(StatusEffect):
    id = "self_control"

    def on_hit(self, ctx: RollContext, stack: int):
        # Логика: 5% за стак
        chance = stack * 5
        # Ограничиваем шанс 100% (на всякий случай, хотя стаков макс 100)
        chance = min(100, chance)

        roll = random.randint(1, 100)

        if roll <= chance:
            # КРИТИЧЕСКИЙ УДАР
            ctx.damage_multiplier *= 2.0
            ctx.is_critical = True

            ctx.log.append(f"💨 CRITICAL HIT! (Chance {chance}%) x2 DMG")

            # Теряем 20 зарядов при успешном крите
            ctx.source.remove_status("self_control", 20)

    def on_turn_end(self, unit, stack) -> list[str]:
        # В конце раунда теряем 20 зарядов
        unit.remove_status("self_control", 20)
        # Если стаков было мало и они ушли в ноль - remove_status сам удалит ключ
        return [f"💨 Self-Control decayed (-20)"]


STATUS_REGISTRY = {
    "strength": StrengthStatus(),
    "bleed": BleedStatus(),
    "paralysis": ParalysisStatus(),
    "self_control": SelfControlStatus(),
}