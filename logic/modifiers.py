# logic/modifiers.py
from dataclasses import dataclass, field

from core.models import Unit


@dataclass
class RollContext:
    source_unit: 'Unit'
    target_unit: 'Unit'
    dice: 'Dice'
    final_value: int

    # Лог изменений, чтобы видеть, откуда взялись цифры (важно для дебага и UI)
    modifiers_log: list = field(default_factory=list)

    def add_power(self, amount: int, source_name: str):
        self.final_value += amount
        self.modifiers_log.append(f"{source_name}: {'+' if amount > 0 else ''}{amount}")