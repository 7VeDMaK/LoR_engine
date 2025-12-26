# engine.py
import random
from core.events import EventManager
from core.models import Unit, Dice
from logic.modifiers import RollContext
from logic.passives import PASSIVE_REGISTRY
from logic.talents import TALENT_REGISTRY


class CombatEngine:
    def __init__(self, seed=None):
        self.events = EventManager()
        self.rng = random.Random(seed)

    def initialize_unit(self, unit: Unit):
        """Подключает пассивки и таланты юнита к событиям"""

        # Passives
        for pid in unit.passives:
            if pid in PASSIVE_REGISTRY:
                self.events.subscribe("BEFORE_ROLL", PASSIVE_REGISTRY[pid])

        # Talents
        for pid in unit.talents:
            if pid in TALENT_REGISTRY:
                self.events.subscribe("BEFORE_ROLL", TALENT_REGISTRY[pid])

    def roll_attack(self, attacker: Unit, defender: Unit, min_d: int, max_d: int):
        # 1. Базовый рандом
        base_roll = self.rng.randint(min_d, max_d)

        # 2. Подготовка контекста
        dice = Dice(min_d, max_d, base_roll)
        ctx = RollContext(attacker, defender, dice, base_roll)
        ctx.log.append(f"[Base Roll] {base_roll}")

        # 3. Запуск событий (Пассивки меняют ctx)
        self.events.emit("BEFORE_ROLL", ctx)

        return ctx