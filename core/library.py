import copy
from core.models import Card, Dice, DiceType

class Library:
    """Хранилище всех пресетов карт в игре"""
    _cards = {}

    @classmethod
    def register(cls, card: Card):
        """Добавляет карту в глобальный реестр"""
        cls._cards[card.name] = card

    @classmethod
    def get_card(cls, name: str) -> Card:
        """Возвращает ПОЛНУЮ КОПИЮ карты, чтобы изменения в бою не ломали оригинал"""
        if name in cls._cards:
            return copy.deepcopy(cls._cards[name])
        # Если карты нет, возвращаем пустышку, чтобы не крашилось
        return Card("Unknown", 0, [])

    @classmethod
    def get_all_names(cls):
        return list(cls._cards.keys())

# --- НАПОЛНЕНИЕ БАЗЫ ДАННЫХ ---
# Здесь мы определяем все карты игры. В будущем это можно грузить из JSON.

# 1. Rampage (Скриншот который ты кидал)
Library.register(Card(
    name="Rampage",
    cost=3,
    description="Жестокая серия атак, вызывающая кровотечение.",
    dice_list=[
        Dice(2, 4, DiceType.BLUNT, effects=["Bleed 1"]),
        Dice(3, 5, DiceType.PIERCE, effects=["Bleed 1"]),
        Dice(3, 5, DiceType.SLASH)
    ]
))

# 2. Iron Defense
Library.register(Card(
    name="Iron Defense",
    cost=2,
    description="Глухая оборона.",
    dice_list=[
        Dice(5, 9, DiceType.BLOCK),
        Dice(5, 8, DiceType.BLOCK),
        Dice(2, 4, DiceType.BLUNT) # Контр-атака
    ]
))

# 3. Evade Master
Library.register(Card(
    name="In The Shadows",
    cost=2,
    description="Попытка уклониться от всего урона.",
    dice_list=[
        Dice(6, 12, DiceType.EVADE, effects=["Restore Light 1"]),
        Dice(4, 8, DiceType.SLASH)
    ]
))

# 4. Heavy Hit
Library.register(Card(
    name="Sledgehammer",
    cost=3,
    description="Один, но очень мощный удар.",
    dice_list=[
        Dice(6, 12, DiceType.BLUNT, effects=["Paralysis 2"])
    ]
))

# 5. Basic
Library.register(Card(
    name="Scratch",
    cost=0,
    description="Слабая атака для восстановления света.",
    dice_list=[
        Dice(2, 5, DiceType.SLASH),
        Dice(2, 4, DiceType.PIERCE)
    ]
))