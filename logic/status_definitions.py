import math
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

# === НОВЫЙ СТАТУС: СТОЙКОСТЬ (ENDURANCE) ===
class EnduranceStatus(StatusEffect):
    id = "endurance"

    def on_roll(self, ctx: RollContext, stack: int):
        # Дает силу только БЛОКУ
        if ctx.dice.dtype == DiceType.BLOCK:
            ctx.modify_power(stack, "Endurance")


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
# SMOKE (ДЫМ) - ОБНОВЛЕННЫЙ
# ==========================================
class SmokeStatus(StatusEffect):
    id = "smoke"

    def _get_limit(self, unit):
        # Базовый лимит 10. Если есть бонус в памяти (от тату), добавляем его.
        bonus = unit.memory.get("smoke_limit_bonus", 0)
        return 10 + bonus

    def on_roll(self, ctx: RollContext, stack: int):
        # Базовый эффект: +1 силы при 9+ стаках
        if stack >= 9:
            ctx.modify_power(1, "Smoke (Base)")

    def get_damage_modifier(self, unit, stack) -> float:
        # Урон скейлится только до 10 стаков (стандартное правило), даже если лимит выше
        eff_stack = min(10, stack)

        if "hiding_in_smoke" in unit.talents:
            return -(eff_stack * 0.03)  # -30% max
        else:
            return eff_stack * 0.05  # +50% max

    def on_turn_end(self, unit, stack) -> list[str]:
        msgs = []

        # 1. Естественный спад (-1)
        unit.remove_status("smoke", 1)
        msgs.append("💨 Smoke decayed (-1)")

        # 2. Проверка лимита (Hard Cap)
        # Получаем актуальное количество после спада
        current = unit.get_status("smoke")
        limit = self._get_limit(unit)

        if current > limit:
            loss = current - limit
            unit.remove_status("smoke", loss)
            msgs.append(f"💨 Smoke cap ({limit}) exceeded. Removed {loss}.")

        return msgs

# === КРАСНЫЙ ЛИКОРИС (STATUS) ===
class RedLycorisStatus(StatusEffect):
    id = "red_lycoris"

    def on_calculate_stats(self, unit) -> dict:
        # Даем огромную инициативу, чтобы "сравняться" (быть не медленнее)
        # А также дикий резист к урону, чтобы эмулировать иммунитет через modifiers
        return {
            "initiative": 999,       # Всегда первый (но prevent_redirection не даст перехватить)
            "damage_take": -9999,    # Технический иммунитет к урону
        }

    def on_turn_end(self, unit, stack) -> list[str]:
        # По окончании действия (когда duration станет 0 и статус пропадет)
        # Логика "Добавить 0.5 S-клеток" пока пропускаем или добавляем в лог
        return []

STATUS_REGISTRY = {
    "strength": StrengthStatus(),
    "bleed": BleedStatus(),
    "endurance": EnduranceStatus(),
    "paralysis": ParalysisStatus(),
    "self_control": SelfControlStatus(),
    "smoke": SmokeStatus(),
    "red_lycoris": RedLycorisStatus(),
}