import unittest
from core.models import Unit, Card, Dice, DiceType
from logic.clash import ClashSystem
from logic.status_definitions import STATUS_REGISTRY


# Наследуемся от TestCase — это стандартный класс для тестов
class TestClashSystem(unittest.TestCase):

    def setUp(self):
        """Этот метод запускается перед КАЖДЫМ тестом. Удобно для подготовки."""
        self.attacker = Unit("Attacker", current_hp=100)
        self.defender = Unit("Defender", current_hp=100)
        self.sys = ClashSystem()

        # Даем заглушки карт, чтобы не падало
        self.attacker.current_card = Card("Atk", dice_list=[])
        self.defender.current_card = Card("Def", dice_list=[])

    def test_strength_bonus(self):
        """Проверяем, что Сила прибавляется к броску"""
        self.attacker.add_status("strength", 5)

        # Создаем кубик, который всегда кидает 5 (min=5, max=5)
        # В реальном коде рандом, но для теста можно подхачить или проверять диапазон
        # Но проще проверить через создание контекста, если мы тестируем чисто математику
        # Или, раз мы тестируем ClashSystem целиком, давай проверим итоговый лог

        dice = Dice(5, 5, DiceType.SLASH)
        self.attacker.current_card.dice_list = [dice]

        # Запускаем бой
        report = self.sys.resolve_card_clash(self.attacker, self.defender)

        # Ожидаем: 5 (база) + 5 (сила) = 10
        roll_log = report[0]['rolls']
        self.assertIn("[10]", roll_log, "Сила не прибавилась к результату!")

    def test_bleed_application(self):
        """Проверяем, что Блид наносит урон при атаке и уменьшается"""
        self.attacker.add_status("bleed", 10)
        dice = Dice(5, 5, DiceType.SLASH)
        self.attacker.current_card.dice_list = [dice]

        self.sys.resolve_card_clash(self.attacker, self.defender)

        # 1. Проверяем урон по себе (было 100, минус 10 блида = 90)
        self.assertEqual(self.attacker.current_hp, 90, "Урон от кровотечения не прошел")

        # 2. Проверяем, что стаки уполовинились (10 // 2 = 5)
        self.assertEqual(self.attacker.get_status("bleed"), 5, "Стаки кровотечения не уменьшились")

    def test_clash_win_interaction(self):
        """Проверяем победу в клеше"""
        # Атакующий кидает 10, Защитник кидает 2
        d1 = Dice(10, 10, DiceType.SLASH)
        d2 = Dice(2, 2, DiceType.SLASH)

        self.attacker.current_card.dice_list = [d1]
        self.defender.current_card.dice_list = [d2]

        report = self.sys.resolve_card_clash(self.attacker, self.defender)

        detail = report[0]['details']
        self.assertIn("Attacker Wins", detail)
        # Защитник должен получить урон: 10 (ролл) * 1.0 (резист) = 10
        self.assertEqual(self.defender.current_hp, 90)


if __name__ == '__main__':
    unittest.main()