import json
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

try:
    from core.card import Card
except ImportError:
    Card = Any


@dataclass
class Resistances:
    slash: float = 1.0
    pierce: float = 1.0
    blunt: float = 1.0

    def to_dict(self): return {"slash": self.slash, "pierce": self.pierce, "blunt": self.blunt}

    @classmethod
    def from_dict(cls, data: dict):
        if not data: return cls()
        return cls(slash=data.get("slash", 1.0), pierce=data.get("pierce", 1.0), blunt=data.get("blunt", 1.0))


@dataclass
class Unit:
    name: str
    level: int = 1
    rank: int = 9
    avatar: Optional[str] = None

    # === РУЧНЫЕ МОДИФИКАТОРЫ ===
    implants_hp_pct: int = 0
    implants_sp_pct: int = 0
    talents_hp_pct: int = 0
    talents_sp_pct: int = 0

    # === БАЗОВЫЕ ===
    base_intellect: int = 1
    base_hp: int = 20
    base_sp: int = 20
    base_speed_min: int = 1
    base_speed_max: int = 4

    # === РАСЧЕТНЫЕ ===
    max_hp: int = 20
    current_hp: int = 20
    max_sp: int = 20
    current_sp: int = 20
    max_stagger: int = 10
    current_stagger: int = 10

    # Скорость: список диапазонов [(min, max), ...]
    computed_speed_dice: List[Tuple[int, int]] = field(default_factory=list)

    # === БОЕВАЯ ФАЗА ===
    # [{'speed': 5, 'card': Card, 'target_slot': 0, 'is_aggro': False}, ...]
    active_slots: List[Dict] = field(default_factory=list)

    # === БРОНЯ ===
    armor_name: str = "Standard Fixer Suit"
    armor_type: str = "Medium"
    hp_resists: 'Resistances' = field(default_factory=lambda: Resistances())
    stagger_resists: 'Resistances' = field(default_factory=lambda: Resistances())

    current_card: Optional['Card'] = None

    # === АТРИБУТЫ ===
    attributes: Dict[str, int] = field(default_factory=lambda: {
        "strength": 0, "endurance": 0, "agility": 0, "wisdom": 0, "psych": 0
    })

    # === НАВЫКИ ===
    skills: Dict[str, int] = field(default_factory=lambda: {
        "strike_power": 0, "medicine": 0, "willpower": 0, "luck": 0,
        "acrobatics": 0, "shields": 0, "tough_skin": 0, "speed": 0,
        "light_weapon": 0, "medium_weapon": 0, "heavy_weapon": 0, "firearms": 0,
        "eloquence": 0, "forging": 0, "engineering": 0, "programming": 0
    })

    _status_effects: Dict[str, List[Dict]] = field(default_factory=dict)
    delayed_queue: List[dict] = field(default_factory=list)
    resources: Dict[str, int] = field(default_factory=dict)

    passives: List[str] = field(default_factory=list)
    talents: List[str] = field(default_factory=list)

    modifiers: Dict[str, int] = field(default_factory=dict)
    level_rolls: Dict[str, Dict[str, int]] = field(default_factory=dict)

    memory: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "name": self.name, "level": self.level, "rank": self.rank, "avatar": self.avatar,
            "base_intellect": self.base_intellect,
            "pct_mods": {"imp_hp": self.implants_hp_pct, "imp_sp": self.implants_sp_pct, "tal_hp": self.talents_hp_pct,
                         "tal_sp": self.talents_sp_pct},
            "base_stats": {"current_hp": self.current_hp, "current_sp": self.current_sp,
                           "current_stagger": self.current_stagger},
            "defense": {"armor_name": self.armor_name, "armor_type": self.armor_type,
                        "hp_resists": self.hp_resists.to_dict(), "stagger_resists": self.stagger_resists.to_dict()},
            "attributes": self.attributes, "skills": self.skills, "passives": self.passives, "talents": self.talents,
            "level_rolls": self.level_rolls
        }

    @classmethod
    def from_dict(cls, data: dict):
        u = cls(name=data.get("name", "Unknown"))
        u.level = data.get("level", 1)
        u.rank = data.get("rank", 9)
        u.avatar = data.get("avatar", None)
        u.base_intellect = data.get("base_intellect", 1)

        pct = data.get("pct_mods", {})
        u.implants_hp_pct = pct.get("imp_hp", 0);
        u.implants_sp_pct = pct.get("imp_sp", 0)
        u.talents_hp_pct = pct.get("tal_hp", 0);
        u.talents_sp_pct = pct.get("tal_sp", 0)

        base = data.get("base_stats", {})
        u.current_hp = base.get("current_hp", 20);
        u.current_sp = base.get("current_sp", 20);
        u.current_stagger = base.get("current_stagger", 10)

        defense = data.get("defense", {})
        u.armor_name = defense.get("armor_name", "Suit");
        u.armor_type = defense.get("armor_type", "Medium")
        u.hp_resists = Resistances.from_dict(defense.get("hp_resists", {}));
        u.stagger_resists = Resistances.from_dict(defense.get("stagger_resists", {}))

        if "attributes" in data: u.attributes.update(data["attributes"])
        if "skills" in data: u.skills.update(data["skills"])
        if "intellect" in u.attributes: del u.attributes["intellect"]

        u.passives = data.get("passives", []);
        u.talents = data.get("talents", []);
        u.level_rolls = data.get("level_rolls", {})

        u.recalculate_stats()
        return u

    def recalculate_stats(self):
        from core.calculations import recalculate_unit_stats
        return recalculate_unit_stats(self)

    # === НОВАЯ ЛОГИКА СКОРОСТИ ===
    def roll_speed_dice(self):
        self.active_slots = []
        for (d_min, d_max) in self.computed_speed_dice:
            mod = self.get_status("haste") - self.get_status("slow") - self.get_status("bind")
            val = random.randint(d_min, d_max) + mod
            val = max(1, val)

            self.active_slots.append({
                'speed': val,
                'card': None,
                'target_slot': None,
                'is_aggro': False  # <--- НОВОЕ ПОЛЕ: ПРИНУДИТЕЛЬНЫЙ КЛЕШ
            })

    # --- МЕТОДЫ ДЛЯ СИМУЛЯТОРА ---
    def is_staggered(self):
        return self.current_stagger <= 0

    def is_dead(self):
        return self.current_hp <= 0

    @property
    def statuses(self) -> Dict[str, int]:
        summary = {}
        for name, instances in self._status_effects.items():
            if sum(i["amount"] for i in instances) > 0: summary[name] = sum(i["amount"] for i in instances)
        return summary

    @property
    def durations(self) -> Dict[str, int]:
        return {}

    def add_status(self, name: str, amount: int, duration: int = 1, delay: int = 0):
        if amount <= 0: return
        if delay > 0: self.delayed_queue.append(
            {"name": name, "amount": amount, "duration": duration, "delay": delay}); return
        if name not in self._status_effects: self._status_effects[name] = []
        if amount > 0: self._status_effects[name].append({"amount": amount, "duration": duration})

    def get_status(self, name: str) -> int:
        if name not in self._status_effects: return 0
        return sum(i["amount"] for i in self._status_effects[name])

    def remove_status(self, name: str, amount: int = None):
        if name not in self._status_effects: return
        if amount is None: del self._status_effects[name]; return
        items = sorted(self._status_effects[name], key=lambda x: x["duration"])
        rem = amount;
        new_items = []
        for item in items:
            if rem <= 0: new_items.append(item); continue
            if item["amount"] > rem:
                item["amount"] -= rem;
                rem = 0;
                new_items.append(item)
            else:
                rem -= item["amount"]
        if not new_items:
            del self._status_effects[name]
        else:
            self._status_effects[name] = new_items

    def heal_hp(self, amount: int):
        eff = 1.0 + self.modifiers.get("heal_efficiency", 0.0)
        final_amt = int(amount * eff)
        if self.get_status("deep_wound") > 0:
            final_amt = int(final_amt * 0.75);
            self.remove_status("deep_wound", 1)
        self.current_hp = min(self.max_hp, self.current_hp + final_amt);
        return final_amt

    def take_sanity_damage(self, amount: int):
        self.current_sp = max(-45, self.current_sp - amount)