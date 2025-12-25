# core/unit.py
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from core.card import Card


@dataclass
class Resistances:
    slash: float = 1.0
    pierce: float = 1.0
    blunt: float = 1.0

    def to_dict(self):
        return {
            "slash": self.slash,
            "pierce": self.pierce,
            "blunt": self.blunt
        }

    @classmethod
    def from_dict(cls, data: dict):
        if not data: return cls()
        return cls(
            slash=data.get("slash", 1.0),
            pierce=data.get("pierce", 1.0),
            blunt=data.get("blunt", 1.0)
        )


@dataclass
class Unit:
    name: str
    # === ОСНОВНЫЕ ПАРАМЕТРЫ ===
    level: int = 1
    rank: int = 9

    # Итоговые (расчетные) значения
    max_hp: int = 100
    current_hp: int = 100
    max_sp: int = 45
    current_sp: int = 45
    max_stagger: int = 50
    current_stagger: int = 50

    # Базовые значения (для формул)
    base_hp: int = 20
    base_sp: int = 20
    base_speed_min: int = 4
    base_speed_max: int = 8

    # === СОПРОТИВЛЕНИЯ И БРОНЯ ===
    armor_name: str = "Standard Fixer Suit"
    armor_type: str = "Medium"
    hp_resists: 'Resistances' = field(default_factory=lambda: Resistances())
    stagger_resists: 'Resistances' = field(default_factory=lambda: Resistances())

    current_card: Optional['Card'] = None

    # === ХАРАКТЕРИСТИКИ ===
    attributes: Dict[str, int] = field(default_factory=lambda: {
        "strength": 1, "endurance": 1, "agility": 1, "wisdom": 1, "psych": 1
    })

    # === НАВЫКИ ===
    skills: Dict[str, int] = field(default_factory=lambda: {
        "strike_power": 0, "medicine": 0, "willpower": 0, "luck": 0,
        "acrobatics": 0, "shields": 0, "tough_skin": 0, "speed": 0,
        "light_weapon": 0, "medium_weapon": 0, "heavy_weapon": 0, "firearms": 0,
        "eloquence": 0, "forging": 0, "engineering": 0, "programming": 0
    })

    # === СТАТУСЫ И ПРОЧЕЕ ===
    _status_effects: Dict[str, List[Dict]] = field(default_factory=dict)
    delayed_queue: List[dict] = field(default_factory=list)
    resources: Dict[str, int] = field(default_factory=dict)

    passives: List[str] = field(default_factory=list)
    talents: List[str] = field(default_factory=list)
    memory: Dict[str, Any] = field(default_factory=dict)

    # --- МЕТОДЫ СЕРИАЛИЗАЦИИ (JSON) ---
    def to_dict(self):
        return {
            "name": self.name,
            "level": self.level,
            "rank": self.rank,
            "stats": {
                "max_hp": self.max_hp, "current_hp": self.current_hp,
                "max_sp": self.max_sp, "current_sp": self.current_sp,
                "max_stagger": self.max_stagger, "current_stagger": self.current_stagger,
                "base_hp": self.base_hp, "base_sp": self.base_sp,
                "base_speed_min": self.base_speed_min, "base_speed_max": self.base_speed_max
            },
            "defense": {
                "armor_name": self.armor_name,
                "armor_type": self.armor_type,
                "hp_resists": self.hp_resists.to_dict(),
                "stagger_resists": self.stagger_resists.to_dict()
            },
            "attributes": self.attributes,
            "skills": self.skills,
            "passives": self.passives,
            "talents": self.talents
        }

    @classmethod
    def from_dict(cls, data: dict):
        # Создаем базовый юнит
        u = cls(name=data.get("name", "Unknown Unit"))

        u.level = data.get("level", 1)
        u.rank = data.get("rank", 9)

        # Stats
        stats = data.get("stats", {})
        u.max_hp = stats.get("max_hp", 100)
        u.current_hp = stats.get("current_hp", 100)
        u.max_sp = stats.get("max_sp", 45)
        u.current_sp = stats.get("current_sp", 45)
        u.max_stagger = stats.get("max_stagger", 50)
        u.current_stagger = stats.get("current_stagger", 50)
        u.base_hp = stats.get("base_hp", 20)
        u.base_sp = stats.get("base_sp", 20)
        u.base_speed_min = stats.get("base_speed_min", 4)
        u.base_speed_max = stats.get("base_speed_max", 8)

        # Defense
        defense = data.get("defense", {})
        u.armor_name = defense.get("armor_name", "Suit")
        u.armor_type = defense.get("armor_type", "Medium")
        u.hp_resists = Resistances.from_dict(defense.get("hp_resists", {}))
        u.stagger_resists = Resistances.from_dict(defense.get("stagger_resists", {}))

        # Dicts (с подстраховкой update, чтобы сохранить дефолтные ключи если их нет в json)
        if "attributes" in data:
            u.attributes.update(data["attributes"])
        if "skills" in data:
            u.skills.update(data["skills"])

        u.passives = data.get("passives", [])
        u.talents = data.get("talents", [])

        return u

    # --- СТАРЫЕ МЕТОДЫ (LOGIC) ---
    @property
    def statuses(self) -> Dict[str, int]:
        summary = {}
        for name, instances in self._status_effects.items():
            total = sum(i["amount"] for i in instances)
            if total > 0: summary[name] = total
        return summary

    @property
    def durations(self) -> Dict[str, int]:
        return {}

    def is_staggered(self):
        return self.current_stagger <= 0

    def is_dead(self):
        return self.current_hp <= 0

    def add_status(self, name: str, amount: int, duration: int = 1, delay: int = 0):
        if amount <= 0: return
        if delay > 0:
            self.delayed_queue.append({"name": name, "amount": amount, "duration": duration, "delay": delay})
            return
        if name not in self._status_effects: self._status_effects[name] = []
        current_total = self.get_status(name)
        if name == "charge" and (current_total + amount) > 20: amount = max(0, 20 - current_total)
        if name == "poise" and (current_total + amount) > 99: amount = max(0, 99 - current_total)
        if amount > 0: self._status_effects[name].append({"amount": amount, "duration": duration})

    def get_status(self, name: str) -> int:
        if name not in self._status_effects: return 0
        return sum(i["amount"] for i in self._status_effects[name])

    def remove_status(self, name: str, amount: int = None):
        if name not in self._status_effects: return
        if amount is None:
            del self._status_effects[name]
            return
        items = sorted(self._status_effects[name], key=lambda x: x["duration"])
        remaining = amount
        new_items = []
        for item in items:
            if remaining <= 0:
                new_items.append(item);
                continue
            if item["amount"] > remaining:
                item["amount"] -= remaining;
                remaining = 0;
                new_items.append(item)
            else:
                remaining -= item["amount"]
        if not new_items:
            del self._status_effects[name]
        else:
            self._status_effects[name] = new_items

    def heal_hp(self, amount: int):
        deep_wound = self.get_status("deep_wound")
        if deep_wound > 0:
            amount = int(amount * 0.75);
            self.remove_status("deep_wound", 1)
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return amount

    def take_sanity_damage(self, amount: int):
        self.current_sp = max(-45, self.current_sp - amount)