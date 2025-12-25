# core/models.py
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

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
    current_val: int = 0
    # Новое поле: список эффектов (например ["Bleed 1", "Paralysis 1"])
    effects: List[str] = field(default_factory=list)

@dataclass
class Card:
    name: str
    cost: int
    dice_list: List[Dice] = field(default_factory=list)
    description: str = "" # Описание карты для UI

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