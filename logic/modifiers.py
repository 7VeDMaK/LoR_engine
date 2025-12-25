from dataclasses import dataclass, field
from typing import List

@dataclass
class RollContext:
    source: 'Unit'
    target: 'Unit'
    dice: 'Dice'
    final_value: int
    log: List[str] = field(default_factory=list)

    def modify_power(self, amount: int, reason: str):
        self.final_value += amount
        sign = "+" if amount > 0 else ""
        self.log.append(f"[{reason}] {sign}{amount}")