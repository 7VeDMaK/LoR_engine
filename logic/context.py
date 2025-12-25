from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

# TYPE_CHECKING нужен, чтобы не было ошибок импорта моделей при запуске
if TYPE_CHECKING:
    from core.models import Unit, Dice

@dataclass
class RollContext:
    """
    Контекст броска кубика. Хранит:
    - source: кто кинул
    - target: в кого (может быть None)
    - dice: сам кубик (данные)
    - final_value: текущее значение силы (меняется статусами)
    - log: история изменений (для отображения игроку)
    """
    source: 'Unit'
    target: Optional['Unit']
    dice: Optional['Dice']
    final_value: int
    log: List[str] = field(default_factory=list)

    def modify_power(self, amount: int, reason: str):
        """Изменяет значение кубика и записывает это в лог."""
        if amount == 0:
            return
        self.final_value += amount
        sign = "+" if amount > 0 else ""
        self.log.append(f"[{reason}] {sign}{amount}")