import random
from core.events import EventManager
from core.models import Unit, Dice
from logic.modifiers import RollContext
from logic.passives import PASSIVE_REGISTRY


class CombatEngine:
    def __init__(self, seed=None):
        self.events = EventManager()
        self.rng = random.Random(seed)

    def initialize_unit(self, unit: Unit):
        """Подключает пассивки юнита к событиям"""
        for pid in unit.passive_ids:
            if pid in PASSIVE_REGISTRY:
                # В полной версии пассивка сама знает свой триггер.
                # Здесь мы жестко привязываем всё к BEFORE_ROLL для простоты.
                self.events.subscribe("BEFORE_ROLL", PASSIVE_REGISTRY[pid])

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