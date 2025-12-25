from dataclasses import dataclass, field
from typing import List, Dict
from core.dice import Dice

@dataclass
class Card:
    name: str
    dice_list: List[Dice] = field(default_factory=list)
    description: str = ""
    id: str = "unknown"
    tier: int = 1
    card_type: str = "melee"
    flags: List[str] = field(default_factory=list)
    scripts: Dict[str, List[Dict]] = field(default_factory=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "tier": self.tier,
            "type": self.card_type,
            "description": self.description,
            "flags": self.flags,
            "scripts": self.scripts,
            "dice": [d.to_dict() for d in self.dice_list]
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id", "unknown"),
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            tier=data.get("tier", 1),
            card_type=data.get("type", "melee"),
            flags=data.get("flags", []),
            scripts=data.get("scripts", {}),
            dice_list=[Dice.from_dict(d) for d in data.get("dice", [])]
        )