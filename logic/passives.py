# logic/passives.py
from logic.modifiers import RollContext

# База данных всех пассивок в игре
PASSIVE_REGISTRY = {}


def register_passive(name):
    def decorator(func):
        PASSIVE_REGISTRY[name] = func
        return func

    return decorator


# Реализация пассивки "Одиночка"
@register_passive("LoneFixer")
def p_lone_fixer(context: RollContext):
    # Условие: проверяем, атакует ли тот, у кого эта пассивка (упрощено)
    # В реальности тут будет проверка context.source_unit.allies_count == 0

    context.add_power(3, "Lone Fixer")