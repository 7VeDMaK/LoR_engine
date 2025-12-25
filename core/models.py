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

@dataclass
class Unit:
    name: str
    max_hp: int = 100
    current_hp: int = 100

    # === НОВОЕ: Рассудок (Sanity / SP) ===
    max_sp: int = 45
    current_sp: int = 45  # Обычно стартует с 0 или 45, сделаем макс для примера

    max_stagger: int = 50
    current_stagger: int = 50

    hp_resists: 'Resistances' = field(default_factory=lambda: Resistances())
    stagger_resists: 'Resistances' = field(default_factory=lambda: Resistances())

    current_card: Optional['Card'] = None

    # === НОВОЕ: Статусы и Ресурсы ===
    # statuses: {"strength": 2, "bleed": 5, "paralysis": 1}
    statuses: Dict[str, int] = field(default_factory=dict)

    # resources: {"ammo": 5, "charge": 0}
    resources: Dict[str, int] = field(default_factory=dict)

    def is_staggered(self):
        return self.current_stagger <= 0

    def is_dead(self):
        return self.current_hp <= 0

    # Хелперы для статусов
    def add_status(self, name: str, amount: int):
        if name not in self.statuses:
            self.statuses[name] = 0
        self.statuses[name] += amount
        # Лимит для некоторых статусов (например, Charge макс 10 без брони)
        if name == "charge" and self.statuses[name] > 10:
            self.statuses[name] = 10  # Упрощенно
        if name == "poise" and self.statuses[name] > 100:
            self.statuses[name] = 100

    def get_status(self, name: str) -> int:
        return self.statuses.get(name, 0)

    def remove_status(self, name: str, amount: int = None):
        """Если amount=None, удаляет полностью"""
        if name in self.statuses:
            if amount is None:
                del self.statuses[name]
            else:
                self.statuses[name] = max(0, self.statuses[name] - amount)
                if self.statuses[name] == 0:
                    del self.statuses[name]

    # Хелперы для лечения/урона (чтобы учесть Глубокую Рану)
    def heal_hp(self, amount: int):
        deep_wound = self.get_status("deep_wound")
        if deep_wound > 0:
            amount = int(amount * 0.75)
            self.remove_status("deep_wound", 1)

        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return amount

    def take_sanity_damage(self, amount: int):
        self.current_sp = max(-45, self.current_sp - amount)


@dataclass
class Resistances:
    slash: float = 1.0
    pierce: float = 1.0
    blunt: float = 1.0