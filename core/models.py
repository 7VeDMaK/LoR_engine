# core/models.py
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


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
    max_sp: int = 45
    current_sp: int = 45
    max_stagger: int = 50
    current_stagger: int = 50

    hp_resists: 'Resistances' = field(default_factory=lambda: Resistances())
    stagger_resists: 'Resistances' = field(default_factory=lambda: Resistances())
    current_card: Optional['Card'] = None

    # === СИСТЕМА СТАТУСОВ (НОВАЯ) ===
    # { "strength": [ {"amount": 2, "duration": 2}, ... ] }
    _status_effects: Dict[str, List[Dict]] = field(default_factory=dict)

    # Очередь отложенных эффектов
    delayed_queue: List[dict] = field(default_factory=list)

    # Ресурсы
    resources: Dict[str, int] = field(default_factory=dict)

    # Списки пассивок и талантов
    passives: List[str] = field(default_factory=list)
    talents: List[str] = field(default_factory=list)

    # === ИСПРАВЛЕНИЕ: ВЕРНУЛ ПОЛЕ MEMORY ===
    # Используется пассивками для хранения промежуточных данных (счетчики ударов и т.д.)
    memory: Dict[str, Any] = field(default_factory=dict)

    @property
    def statuses(self) -> Dict[str, int]:
        """Сводка статусов для совместимости."""
        summary = {}
        for name, instances in self._status_effects.items():
            total = sum(i["amount"] for i in instances)
            if total > 0:
                summary[name] = total
        return summary

    @property
    def durations(self) -> Dict[str, int]:
        """Заглушка."""
        return {}

    def is_staggered(self):
        return self.current_stagger <= 0

    def is_dead(self):
        return self.current_hp <= 0

    def add_status(self, name: str, amount: int, duration: int = 1, delay: int = 0):
        if amount <= 0: return

        if delay > 0:
            self.delayed_queue.append({
                "name": name,
                "amount": amount,
                "duration": duration,
                "delay": delay
            })
            return

        if name not in self._status_effects:
            self._status_effects[name] = []

        # Лимиты
        current_total = self.get_status(name)
        if name == "charge" and (current_total + amount) > 20:
            amount = max(0, 20 - current_total)
        if name == "poise" and (current_total + amount) > 99:
            amount = max(0, 99 - current_total)

        if amount > 0:
            self._status_effects[name].append({
                "amount": amount,
                "duration": duration
            })

    def get_status(self, name: str) -> int:
        if name not in self._status_effects:
            return 0
        return sum(i["amount"] for i in self._status_effects[name])

    def remove_status(self, name: str, amount: int = None):
        if name not in self._status_effects:
            return

        if amount is None:
            del self._status_effects[name]
            return

        items = sorted(self._status_effects[name], key=lambda x: x["duration"])

        remaining_to_remove = amount
        new_items = []

        for item in items:
            if remaining_to_remove <= 0:
                new_items.append(item)
                continue

            if item["amount"] > remaining_to_remove:
                item["amount"] -= remaining_to_remove
                remaining_to_remove = 0
                new_items.append(item)
            else:
                remaining_to_remove -= item["amount"]

        if not new_items:
            del self._status_effects[name]
        else:
            self._status_effects[name] = new_items

    def heal_hp(self, amount: int):
        deep_wound = self.get_status("deep_wound")
        if deep_wound > 0:
            amount = int(amount * 0.75)
            self.remove_status("deep_wound", 1)
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return amount

    def take_sanity_damage(self, amount: int):
        self.current_sp = max(-45, self.current_sp - amount)