from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from core.card import Card

@dataclass
class Resistances:
    slash: float = 1.0
    pierce: float = 1.0
    blunt: float = 1.0

@dataclass
class Unit:
    name: str
    # === ОСНОВНЫЕ ПАРАМЕТРЫ ===
    level: int = 1
    rank: int = 9

    # Итоговые (расчетные) значения.
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
    armor_type: str = "Medium"  # Light, Medium, Heavy
    hp_resists: 'Resistances' = field(default_factory=lambda: Resistances())
    stagger_resists: 'Resistances' = field(default_factory=lambda: Resistances())

    current_card: Optional['Card'] = None

    # === ХАРАКТЕРИСТИКИ (ATTRIBUTES) ===
    attributes: Dict[str, int] = field(default_factory=lambda: {
        "strength": 1,
        "endurance": 1,
        "agility": 1,
        "wisdom": 1,
        "psych": 1
    })

    # === НАВЫКИ (SKILLS) ===
    skills: Dict[str, int] = field(default_factory=lambda: {
        # --- Боевые / Физические ---
        "strike_power": 0,  # Сила удара
        "medicine": 0,  # Медицина
        "willpower": 0,  # Сила воли (Выдержка)
        "luck": 0,  # Удача
        "acrobatics": 0,  # Акробатика
        "shields": 0,  # Щиты
        "tough_skin": 0,  # Крепкая кожа
        "speed": 0,  # Скорость

        # --- Владение оружием ---
        "light_weapon": 0,  # Легкое оружие
        "medium_weapon": 0,  # Среднее оружие
        "heavy_weapon": 0,  # Тяжелое оружие
        "firearms": 0,  # Огнестрельное оружие

        # --- Социальные / Крафт / Техника ---
        "eloquence": 0,  # Красноречие
        "forging": 0,  # Ковка
        "engineering": 0,  # Инженерия
        "programming": 0  # Программирование
    })

    # === СИСТЕМА СТАТУСОВ ===
    _status_effects: Dict[str, List[Dict]] = field(default_factory=dict)
    delayed_queue: List[dict] = field(default_factory=list)
    resources: Dict[str, int] = field(default_factory=dict)

    # Пассивки, Таланты, Память боя
    passives: List[str] = field(default_factory=list)
    talents: List[str] = field(default_factory=list)
    memory: Dict[str, Any] = field(default_factory=dict)

    @property
    def statuses(self) -> Dict[str, int]:
        summary = {}
        for name, instances in self._status_effects.items():
            total = sum(i["amount"] for i in instances)
            if total > 0:
                summary[name] = total
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

        if amount > 0:
            self._status_effects[name].append({"amount": amount, "duration": duration})

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
                new_items.append(item)
                continue
            if item["amount"] > remaining:
                item["amount"] -= remaining
                remaining = 0
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
            amount = int(amount * 0.75)
            self.remove_status("deep_wound", 1)
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return amount

    def take_sanity_damage(self, amount: int):
        self.current_sp = max(-45, self.current_sp - amount)