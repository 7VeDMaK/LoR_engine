# engine.py
import random
from core.events import EventManager
from core.models import Unit, Dice
from logic.modifiers import RollContext
from logic.passives import PASSIVE_REGISTRY


class CombatEngine:
    def __init__(self):
        self.events = EventManager()
        self.rng = random.Random(42)  # Фиксированный seed для детерминированности

    def initialize_unit(self, unit: Unit):
        """Подключает пассивки юнита к шине событий"""
        for pid in unit.passive_ids:
            if pid in PASSIVE_REGISTRY:
                passive_func = PASSIVE_REGISTRY[pid]
                # Подписываем пассивку на событие "BEFORE_ROLL"
                # В сложной системе пассивка сама скажет, на какие события ей надо
                self.events.subscribe("BEFORE_ROLL", passive_func, priority=50)

    def roll_dice(self, unit: Unit, target: Unit, dice: Dice):
        # 1. Кидаем "сырой" кубик
        raw_roll = self.rng.randint(dice.min_val, dice.max_val)

        # 2. Создаем контекст (коробку с данными)
        context = RollContext(
            source_unit=unit,
            target_unit=target,
            dice=dice,
            final_value=raw_roll
        )

        # 3. Кричим в чат: "Мы собираемся зафиксировать бросок! Кто хочет поменять?"
        self.events.emit("BEFORE_ROLL", context)

        return context