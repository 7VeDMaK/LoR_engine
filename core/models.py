# core/models.py
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict


class DiceType(Enum):
    SLASH = "Slash"
    PIERCE = "Pierce"
    BLUNT = "Blunt"
    BLOCK = "Block"
    EVADE = "Evade"


@dataclass
class Dice:
    min_val: int
    max_val: int
    dtype: DiceType
    scripts: Dict[str, List[Dict]] = field(default_factory=dict)

    # ... (твой метод from_dict оставляем) ...

    # === ДОБАВЛЯЕМ ЭТОТ МЕТОД ===
    def to_dict(self):
        return {
            "type": self.dtype.value.lower(),  # Превращаем Enum в строку "slash"
            "base_min": self.min_val,
            "base_max": self.max_val,
            "scripts": self.scripts
        }

    @classmethod
    def from_dict(cls, data: dict):
        # (Твой старый код from_dict)
        # Просто убедись что он совпадает с тем что я давал ранее
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

    # === ДОБАВЛЯЕМ ЭТОТ МЕТОД ===
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
        # (Твой код from_dict, убедись что он возвращает объект)
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


# ... (Остальные классы Unit, Resistances без изменений)

@dataclass
class Resistances:
    slash: float = 1.0
    pierce: float = 1.0
    blunt: float = 1.0


@dataclass
class Unit:
    name: str
    max_hp: int = 100
    current_hp: int = 100
    max_stagger: int = 50
    current_stagger: int = 50
    hp_resists: Resistances = field(default_factory=Resistances)
    stagger_resists: Resistances = field(default_factory=Resistances)
    current_card: Optional[Card] = None

    def is_staggered(self):
        return self.current_stagger <= 0