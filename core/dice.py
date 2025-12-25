from dataclasses import dataclass, field
from typing import List, Dict
from core.enums import DiceType

@dataclass
class Dice:
    min_val: int
    max_val: int
    dtype: DiceType
    scripts: Dict[str, List[Dict]] = field(default_factory=dict)

    def to_dict(self):
        return {
            "type": self.dtype.value.lower(),
            "base_min": self.min_val,
            "base_max": self.max_val,
            "scripts": self.scripts
        }

    @classmethod
    def from_dict(cls, data: dict):
        type_map = {
            "attack": DiceType.SLASH, "slash": DiceType.SLASH,
            "pierce": DiceType.PIERCE, "blunt": DiceType.BLUNT,
            "block": DiceType.BLOCK, "evade": DiceType.EVADE
        }
        json_type = data.get("type", "slash").lower()
        dtype = type_map.get(json_type, DiceType.SLASH)
        return cls(
            min_val=data.get("base_min", 1),
            max_val=data.get("base_max", 1),
            dtype=dtype,
            scripts=data.get("scripts", {})
        )