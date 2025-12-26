import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

try:
    from core.card import Card
except ImportError:
    Card = Any

from core.resistances import Resistances
# Импортируем наши новые миксины
from core.unit_mixins import UnitStatusMixin, UnitCombatMixin, UnitLifecycleMixin


@dataclass
class Unit(UnitStatusMixin, UnitCombatMixin, UnitLifecycleMixin):
    # === ОСНОВНАЯ ИНФОРМАЦИЯ ===
    name: str
    level: int = 1
    rank: int = 9
    avatar: Optional[str] = None

    # === МОДИФИКАТОРЫ ПРОЦЕНТОВ (Импланты/Таланты) ===
    implants_hp_pct: int = 0
    implants_sp_pct: int = 0
    talents_hp_pct: int = 0
    talents_sp_pct: int = 0

    # === БАЗОВЫЕ ПАРАМЕТРЫ (из редактора) ===
    base_intellect: int = 1
    base_hp: int = 20
    base_sp: int = 20
    base_speed_min: int = 1
    base_speed_max: int = 4

    # === РАСЧЕТНЫЕ ПАРАМЕТРЫ (в бою) ===
    max_hp: int = 20
    current_hp: int = 20
    max_sp: int = 20
    current_sp: int = 20
    max_stagger: int = 10
    current_stagger: int = 10

    deck: List[str] = field(default_factory=list)

    # === БОЕВАЯ СИСТЕМА (Слоты и Скорость) ===
    computed_speed_dice: List[Tuple[int, int]] = field(default_factory=list)
    active_slots: List[Dict] = field(default_factory=list)
    current_card: Optional['Card'] = None

    # === СИСТЕМА СПОСОБНОСТЕЙ ===
    cooldowns: Dict[str, int] = field(default_factory=dict)
    active_buffs: Dict[str, int] = field(default_factory=dict)

    # === ЗАЩИТА ===
    armor_name: str = "Standard Fixer Suit"
    armor_type: str = "Medium"
    hp_resists: Resistances = field(default_factory=lambda: Resistances())
    stagger_resists: Resistances = field(default_factory=lambda: Resistances())

    # === RPG СИСТЕМА (Атрибуты/Навыки/Таланты) ===
    attributes: Dict[str, int] = field(default_factory=lambda: {
        "strength": 0, "endurance": 0, "agility": 0, "wisdom": 0, "psych": 0
    })

    skills: Dict[str, int] = field(default_factory=lambda: {
        "strike_power": 0, "medicine": 0, "willpower": 0, "luck": 0,
        "acrobatics": 0, "shields": 0, "tough_skin": 0, "speed": 0,
        "light_weapon": 0, "medium_weapon": 0, "heavy_weapon": 0, "firearms": 0,
        "eloquence": 0, "forging": 0, "engineering": 0, "programming": 0
    })

    passives: List[str] = field(default_factory=list)
    talents: List[str] = field(default_factory=list)
    level_rolls: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # === ВНУТРЕННЕЕ СОСТОЯНИЕ ===
    _status_effects: Dict[str, List[Dict]] = field(default_factory=dict)
    delayed_queue: List[dict] = field(default_factory=list)
    resources: Dict[str, int] = field(default_factory=dict)
    modifiers: Dict[str, int] = field(default_factory=dict)
    memory: Dict[str, Any] = field(default_factory=dict)

    def recalculate_stats(self):
        # Оставляем этот вызов, так как он связывает Unit с модулем calculations
        from core.calculations import recalculate_unit_stats
        return recalculate_unit_stats(self)

    # === СЕРИАЛИЗАЦИЯ (TO/FROM DICT) ===
    # Это чисто технический код для сохранения/загрузки, ему здесь самое место

    def to_dict(self):
        return {
            "name": self.name, "level": self.level, "rank": self.rank, "avatar": self.avatar,
            "base_intellect": self.base_intellect,
            "pct_mods": {
                "imp_hp": self.implants_hp_pct, "imp_sp": self.implants_sp_pct,
                "tal_hp": self.talents_hp_pct, "tal_sp": self.talents_sp_pct
            },
            "deck": self.deck,
            "base_stats": {
                "current_hp": self.current_hp, "current_sp": self.current_sp,
                "current_stagger": self.current_stagger
            },
            "defense": {
                "armor_name": self.armor_name, "armor_type": self.armor_type,
                "hp_resists": self.hp_resists.to_dict(),
                "stagger_resists": self.stagger_resists.to_dict()
            },
            "attributes": self.attributes,
            "skills": self.skills,
            "passives": self.passives,
            "talents": self.talents,
            "level_rolls": self.level_rolls,
            "cooldowns": self.cooldowns,
            "active_buffs": self.active_buffs
        }

    @classmethod
    def from_dict(cls, data: dict):
        u = cls(name=data.get("name", "Unknown"))

        # Основные статы
        u.level = data.get("level", 1)
        u.rank = data.get("rank", 9)
        u.avatar = data.get("avatar", None)
        u.base_intellect = data.get("base_intellect", 1)

        u.deck = data.get("deck", [])

        # Модификаторы
        pct = data.get("pct_mods", {})
        u.implants_hp_pct = pct.get("imp_hp", 0)
        u.implants_sp_pct = pct.get("imp_sp", 0)
        u.talents_hp_pct = pct.get("tal_hp", 0)
        u.talents_sp_pct = pct.get("tal_sp", 0)

        # Текущее состояние
        base = data.get("base_stats", {})
        u.current_hp = base.get("current_hp", 20)
        u.current_sp = base.get("current_sp", 20)
        u.current_stagger = base.get("current_stagger", 10)

        # Защита
        defense = data.get("defense", {})
        u.armor_name = defense.get("armor_name", "Suit")
        u.armor_type = defense.get("armor_type", "Medium")
        u.hp_resists = Resistances.from_dict(defense.get("hp_resists", {}))
        u.stagger_resists = Resistances.from_dict(defense.get("stagger_resists", {}))

        # Словари данных
        if "attributes" in data: u.attributes.update(data["attributes"])
        if "skills" in data: u.skills.update(data["skills"])
        # Очистка legacy поля
        if "intellect" in u.attributes: del u.attributes["intellect"]

        u.passives = data.get("passives", [])
        u.talents = data.get("talents", [])
        u.level_rolls = data.get("level_rolls", {})

        # Активки
        u.cooldowns = data.get("cooldowns", {})
        u.active_buffs = data.get("active_buffs", {})

        u.recalculate_stats()
        return u