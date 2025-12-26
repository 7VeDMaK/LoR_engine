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

    # === НОВЫЙ МЕТОД ДЛЯ МОДИФИКАТОРОВ УРОНА ===
    def get_damage_modifier(self, unit, stack) -> float:
        """Возвращает % изменения урона (0.1 = +10%, -0.2 = -20%)"""
        return 0.0


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


# ==========================================
# SMOKE (ДЫМ)
# ==========================================
class SmokeStatus(StatusEffect):
    id = "smoke"

    def on_roll(self, ctx: RollContext, stack: int):
        # Если 9 или больше стаков -> все дайсы получают +1 силы
        # Ограничиваем эффективные стаки до 10, но условие >= 9 работает и при 20
        if stack >= 9:
            ctx.modify_power(1, "Smoke")

    def get_damage_modifier(self, unit, stack) -> float:
        # Ограничиваем максимум 10 стаков для расчета процентов
        eff_stack = min(10, stack)

        # Проверяем наличие таланта 6.1
        if "hiding_in_smoke" in unit.talents:
            # С талантом: -3% входящего урона за стак (макс -30%)
            return -(eff_stack * 0.03)
        else:
            # Без таланта: +5% входящего урона за стак (макс +50%)
            return eff_stack * 0.05

    def on_turn_end(self, unit, stack) -> list[str]:
        # Теряет 1 стак в конце сцены
        unit.remove_status("smoke", 1)
        return ["💨 Smoke decayed (-1)"]

STATUS_REGISTRY = {
    "strength": StrengthStatus(),
    "bleed": BleedStatus(),
    "paralysis": ParalysisStatus(),
    "self_control": SelfControlStatus(),
"smoke": SmokeStatus(),
}