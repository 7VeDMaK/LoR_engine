# main.py
from core.models import Unit, CombatStats, Dice
from engine import CombatEngine
import logic.passives  # Важно импортировать, чтобы декораторы сработали!


def main():
    # 1. Создаем движок
    engine = CombatEngine()

    # 2. Создаем бойцов
    # Роланд имеет пассивку LoneFixer
    roland = Unit("Roland", CombatStats(hp=100, stagger=50), passive_ids=["LoneFixer"])
    argalia = Unit("Argalia", CombatStats(hp=120, stagger=60))

    # 3. Инициализируем (подключаем провода/пассивки)
    engine.initialize_unit(roland)
    engine.initialize_unit(argalia)

    # 4. Создаем атаку (кубик 4-8)
    attack_dice = Dice(min_val=4, max_val=8)

    print(f"--- Атака: {roland.name} бьет {argalia.name} ---")

    # 5. Просчитываем бросок
    result_context = engine.roll_dice(roland, argalia, attack_dice)

    # 6. Вывод результата
    print(
        f"Базовый бросок: {result_context.final_value - sum(int(x.split(':')[1]) for x in result_context.modifiers_log)}")
    # ^ (немного костыльно вычитаем, чтобы показать базу, но суть ясна)

    print("Примененные эффекты:")
    for log in result_context.modifiers_log:
        print(f" -> {log}")

    print(f"ИТОГОВЫЙ БРОСОК: {result_context.final_value}")


if __name__ == "__main__":
    main()