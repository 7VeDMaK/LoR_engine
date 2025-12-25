from logic.context import RollContext
from core.models import DiceType


class StatusEffect:
    id = "base"

    # --- CARD EVENTS ---
    def on_use(self, unit, card, log_func):
        """Срабатывает при использовании карты (до бросков)."""
        pass

    def on_combat_start(self, unit, log_func):
        """Перед началом столкновения (Clash Phase)."""
        pass

    def on_combat_end(self, unit, log_func):
        """После завершения всех бросков карты."""
        pass

    # --- DICE EVENTS ---
    def on_roll(self, ctx: RollContext, stack: int):
        """
        Срабатывает после броска, но до сравнения.
        Здесь применяем Силу, Слабость или условные бонусы
        (например: +2 если выпал максимум).
        """
        pass

    def on_clash_win(self, ctx: RollContext, stack: int):
        """Срабатывает при победе в столкновении."""
        pass

    def on_clash_lose(self, ctx: RollContext, stack: int):
        """Срабатывает при поражении в столкновении."""
        pass

    def on_hit(self, ctx: RollContext, stack: int):
        """
        Срабатывает при успешном нанесении урона (атака)
        или успешном блоке (защита).
        """
        pass

    # --- TURN EVENTS ---
    def on_turn_end(self, unit, stack) -> list[str]:
        """Конец раунда (сброс статусов, урон от ожогов)."""
        return []


# === ПРИМЕРЫ РЕАЛИЗАЦИИ ===

class StrengthStatus(StatusEffect):
    id = "strength"

    def on_roll(self, ctx: RollContext, stack: int):
        # Добавляем силу только атакующим кубикам
        if ctx.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            ctx.modify_power(stack, "Strength")

    def on_turn_end(self, unit, stack):
        unit.remove_status("strength")
        return []


class BleedStatus(StatusEffect):
    id = "bleed"

    def on_roll(self, ctx: RollContext, stack: int):
        # Кровотечение срабатывает при попытке атаки (во время броска)
        if ctx.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            dmg = stack
            ctx.source.current_hp -= dmg

            # Логика: снимаем половину стаков (округляя вниз)
            # Если нужно снимать 1 стак за удар - меняем логику тут.
            new_stack = stack // 2
            if new_stack > 0:
                ctx.source.statuses["bleed"] = new_stack
            else:
                ctx.source.remove_status("bleed")

            # Пишем в лог контекста, чтобы видно было прямо во время удара
            ctx.log.append(f"🩸 Bleed: {ctx.source.name} takes {dmg} dmg")

    def on_turn_end(self, unit, stack):
        # Если кровотечение не было использовано, оно исчезает в конце хода
        unit.remove_status("bleed")
        return ["Bleed expired"]


class ParalysisStatus(StatusEffect):
    id = "paralysis"

    def on_roll(self, ctx: RollContext, stack: int):
        # Паралич: -3 силы (пример), снимается 1 стак при срабатывании
        ctx.modify_power(-3, "Paralysis")
        ctx.source.remove_status("paralysis", 1)


# === РЕЕСТР ===
STATUS_REGISTRY = {
    "strength": StrengthStatus(),
    "bleed": BleedStatus(),
    "paralysis": ParalysisStatus(),
    # "burn": BurnStatus(), и т.д.
}