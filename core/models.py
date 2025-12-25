# core/models.py
from dataclasses import dataclass, field
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

    # === СИСТЕМА СТАТУСОВ ===
    # Текущие активные статусы {name: amount}
    statuses: Dict[str, int] = field(default_factory=dict)

    # Длительность активных статусов {name: turns_left}
    # Если статуса нет в этом словаре, считается duration=1 (только этот ход)
    durations: Dict[str, int] = field(default_factory=dict)

    # Очередь отложенных эффектов (Delay)
    # List of {"name": str, "amount": int, "duration": int, "delay": int}
    delayed_queue: List[dict] = field(default_factory=list)
    # ========================

    resources: Dict[str, int] = field(default_factory=dict)

    def is_staggered(self):
        return self.current_stagger <= 0

    def is_dead(self):
        return self.current_hp <= 0

    def add_status(self, name: str, amount: int, duration: int = 1, delay: int = 0):
        """
        Добавляет статус.
        :param duration: Сколько ходов длится эффект (по умолчанию 1).
        :param delay: Через сколько ходов активируется (0 = сразу).
        """
        # 1. Если есть задержка - в очередь
        if delay > 0:
            self.delayed_queue.append({
                "name": name,
                "amount": amount,
                "duration": duration,
                "delay": delay
            })
            return

        # 2. Если задержки нет - применяем сразу
        if name not in self.statuses:
            self.statuses[name] = 0
        self.statuses[name] += amount

        # Лимиты
        if name == "charge" and self.statuses[name] > 20: self.statuses[name] = 20
        if name == "poise" and self.statuses[name] > 99: self.statuses[name] = 99

        # Обновляем длительность (берем максимум из текущей и новой)
        current_dur = self.durations.get(name, 0)
        self.durations[name] = max(current_dur, duration)

    def get_status(self, name: str) -> int:
        return self.statuses.get(name, 0)

    def remove_status(self, name: str, amount: int = None):
        """Удаляет стаки. Если 0 - удаляет статус целиком."""
        if name in self.statuses:
            if amount is None:
                del self.statuses[name]
                if name in self.durations: del self.durations[name]
            else:
                self.statuses[name] = max(0, self.statuses[name] - amount)
                if self.statuses[name] == 0:
                    del self.statuses[name]
                    if name in self.durations: del self.durations[name]

    def heal_hp(self, amount: int):
        deep_wound = self.get_status("deep_wound")
        if deep_wound > 0:
            amount = int(amount * 0.75)
            self.remove_status("deep_wound", 1)
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return amount

    def take_sanity_damage(self, amount: int):
        self.current_sp = max(-45, self.current_sp - amount)