from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING, Optional

# TYPE_CHECKING нужен, чтобы не было кругового импорта (ImportError: circular import),
# так как Unit может ссылаться на modifiers, а modifiers на Unit.
if TYPE_CHECKING:
    from core.models import Unit, Dice


@dataclass
class RollContext:
    """
    Контекст броска кубика. Хранит кто кинул, в кого, какой кубик и историю изменений силы.
    """
    source: 'Unit'
    target: Optional['Unit']
    dice: 'Dice'
    final_value: int
    log: List[str] = field(default_factory=list)

    def modify_power(self, amount: int, reason: str):
        """Изменяет значение кубика и записывает это в лог."""
        if amount == 0:
            return
        self.final_value += amount
        sign = "+" if amount > 0 else ""
        self.log.append(f"[{reason}] {sign}{amount}")


class ModifierSystem:
    """
    Класс, отвечающий за применение модификаторов к броску.
    Необходим для работы logic/clash.py.
    """

    @staticmethod
    def apply_modifiers(context: RollContext):
        """
        Применяет базовые статусы (Сила, Слабость и т.д.) к контексту.
        """
        unit = context.source

        # 1. Сила (Strength)
        strength = unit.get_status("strength")
        if strength > 0:
            context.modify_power(strength, "Strength")

        # 2. Слабость (Weakness/Feeble)
        weakness = unit.get_status("weakness")
        if weakness > 0:
            context.modify_power(-weakness, "Weakness")

        # 3. Разоружение (Disarm) - уменьшает защитные кубики
        # (Проверку типа кубика лучше делать здесь, но для примера упростим)
        disarm = unit.get_status("disarm")
        if disarm > 0:
            # Тут нужна проверка, является ли кубик защитным,
            # но пока просто оставим логику, чтобы класс не был пустым
            pass

        return context