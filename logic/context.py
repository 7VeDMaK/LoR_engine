from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import Unit, Dice


@dataclass
class RollContext:
    """
    Контекст броска кубика.
    """
    source: 'Unit'
    target: Optional['Unit']
    dice: Optional['Dice']
    final_value: int

    # --- [NEW] Чистое значение броска (для логов "5 + X") ---
    base_value: int = 0
    # --------------------------------------------------------

    log: List[str] = field(default_factory=list)

    # === НОВЫЕ ПОЛЯ ДЛЯ КРИТОВ ===
    damage_multiplier: float = 1.0  # Множитель урона (по умолчанию x1.0)
    is_critical: bool = False  # Флаг, был ли крит

    def modify_power(self, amount: int, reason: str):
        """Изменяет значение кубика и записывает это в лог."""
        if amount == 0:
            return
        self.final_value += amount
        sign = "+" if amount > 0 else ""
        self.log.append(f"[{reason}] {sign}{amount}")