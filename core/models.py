# core/models.py
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class CombatStats:
    hp: int
    stagger: int
    light: int = 3

@dataclass
class Unit:
    name: str
    stats: CombatStats
    # Юнит сам не знает, как работают его пассивки. Он просто хранит их названия/ID.
    passive_ids: List[str] = field(default_factory=list)

@dataclass
class Dice:
    min_val: int
    max_val: int
    current_val: int = 0  # Сюда запишем результат после всех баффов