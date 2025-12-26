# logic/card_scripts.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logic.modifiers import RollContext


def apply_status(context: 'RollContext', params: dict):
    status_name = params.get("status")
    stack = params.get("stack", 1)
    target_type = params.get("target", "target")  # "self", "target", "all"

    # Читаем параметры длительности
    duration = int(params.get("duration", 1))
    delay = int(params.get("delay", 0))

    # === НОВАЯ ЛОГИКА: МИНИМАЛЬНЫЙ БРОСОК ===
    min_roll = params.get("min_roll")
    if min_roll is not None:
        # Проверяем значение броска
        # Примечание: context.final_value включает бонусы силы.
        # Для "чистого" броска потребовались бы изменения в ядре,
        # но для кубика 1-2 с условием 2 это работает корректно.
        if context.final_value < int(min_roll):
            return
            # ========================================

    # === ХАК ДЛЯ ДЫМА ===
    # Дым всегда должен быть "вечным", так как у него своя механика спада.
    if status_name == "smoke":
        duration = 99

    # 1. Формируем список целей
    targets_to_affect = []

    if target_type == "self":
        targets_to_affect.append(context.source)
    elif target_type == "target":
        targets_to_affect.append(context.target)
    elif target_type == "all":
        # Если цель "all" — добавляем обоих (если они существуют)
        if context.source: targets_to_affect.append(context.source)
        if context.target: targets_to_affect.append(context.target)

    if not status_name: return

    # 2. Применяем статус ко всем выбранным целям
    for unit in targets_to_affect:
        # Дополнительная защита от None (на случай странных контекстов)
        if not unit: continue

        unit.add_status(status_name, stack, duration=duration, delay=delay)

        # Формируем красивый лог
        extras = []
        # Не показываем "99 turns" для дыма, чтобы не засорять лог, или если длительность > 1
        if 1 < duration < 90:
            extras.append(f"{duration} turns")
        if delay > 0:
            extras.append(f"in {delay} turns")

        extra_str = f" ({', '.join(extras)})" if extras else ""

        # Иконка зависит от того, кто получил статус (👤 - сам, 🎯 - враг)
        tgt_icon = "👤" if unit == context.source else "🎯"

        context.log.append(f"🧪 {status_name.capitalize()} +{stack}{extra_str} to {tgt_icon}{unit.name}")


def multiply_status(context: 'RollContext', params: dict):
    status_name = params.get("status")
    multiplier = float(params.get("multiplier", 2.0))  # По умолчанию х2
    target_type = params.get("target", "target")

    unit = context.target if target_type == "target" else context.source
    if not unit or not status_name: return

    # 1. Получаем текущее кол-во
    current_stack = unit.get_status(status_name)

    if current_stack > 0:
        # 2. Считаем, сколько нужно ДОБАВИТЬ, чтобы получить множитель
        # Пример: Было 5. Хотим х2 (10). Нужно добавить 5.
        # Формула: add = current * (multiplier - 1)
        amount_to_add = int(current_stack * (multiplier - 1))

        if amount_to_add > 0:
            duration = 99 if status_name == "smoke" else 1
            unit.add_status(status_name, amount_to_add, duration=duration)

            context.log.append(f"🌫️ Doubled {status_name} on {unit.name} (+{amount_to_add})")
    else:
        # (Опционально)
        # context.log.append(f"No {status_name} to multiply")
        pass

def restore_hp(context: 'RollContext', params: dict):
    amount = params.get("amount", 0)
    target_type = params.get("target", "self")

    # Определяем цель лечения
    unit_to_heal = context.source if target_type == "self" else context.target

    # Определяем ИСТОЧНИК лечения
    healer = context.source

    if unit_to_heal:
        # Используем try/except для совместимости.
        # Если ваш unit.py поддерживает source_unit — сработает первый вариант.
        # Если нет — сработает второй, и игра не вылетит.
        try:
            actual_heal = unit_to_heal.heal_hp(amount, source_unit=healer)
        except TypeError:
            actual_heal = unit_to_heal.heal_hp(amount)

        msg = f"💚 {healer.name} healed {actual_heal} HP ({unit_to_heal.name})"

        # Если хил был порезан пассивкой (проверка для логов)
        if actual_heal < amount and "daughter_of_backstreets" in getattr(unit_to_heal, 'passives',
                                                                         []) and healer != unit_to_heal:
            msg += " (Reduced by Passive)"

        context.log.append(msg)


def steal_status(context: 'RollContext', params: dict):
    status_name = params.get("status")
    if not status_name: return

    # Кто крадет (Source) и у кого (Target)
    thief = context.source
    victim = context.target

    if not thief or not victim: return

    # 1. Узнаем, сколько статуса у жертвы
    amount_to_steal = victim.get_status(status_name)

    if amount_to_steal > 0:
        # 2. Удаляем весь статус у жертвы
        victim.remove_status(status_name, amount_to_steal)

        # 3. Начисляем статус вору
        # Для Дыма ставим 99 ходов (вечность), для остальных берем из параметров или 1
        duration = 99 if status_name == "smoke" else int(params.get("duration", 1))

        thief.add_status(status_name, amount_to_steal, duration=duration)

        # Лог
        context.log.append(f"💨 Stole {amount_to_steal} {status_name.capitalize()} from {victim.name}")
    else:
        # (Опционально) Можно написать, что красть было нечего
        # context.log.append(f"💨 No {status_name} to steal")
        pass

def deal_custom_damage(context: 'RollContext', params: dict):
    dmg_type = params.get("type", "stagger")  # "hp", "stagger"
    scale = float(params.get("scale", 1.0))
    target_mode = params.get("target", "target")
    prevent_standard = params.get("prevent_standard", False)

    # 1. Рассчитываем базовое значение урона (Бросок * Множитель)
    base_amount = int(context.final_value * scale)

    # 2. Определяем список целей
    targets = []
    if target_mode == "target":
        targets.append(context.target)
    elif target_mode == "self":
        targets.append(context.source)
    elif target_mode == "all":
        # Mass Attack: И по себе, и по врагу
        if context.source: targets.append(context.source)
        if context.target: targets.append(context.target)

    # 3. Наносим урон каждой цели
    dtype_name = context.dice.dtype.value.lower() if context.dice else "slash"

    for unit in targets:
        if not unit: continue

        final_dmg = base_amount

        if dmg_type == "stagger":
            # Учитываем резисты к Stagger
            res = getattr(unit.stagger_resists, dtype_name, 1.0)
            final_dmg = int(final_dmg * res)

            unit.current_stagger -= final_dmg

            # Логгирование
            tgt_icon = "👤" if unit == context.source else "🎯"
            context.log.append(f"😵 {tgt_icon}{unit.name} -{final_dmg} Stagger (x{scale})")

        elif dmg_type == "hp":
            # Учитываем резисты к HP
            res = getattr(unit.hp_resists, dtype_name, 1.0)
            final_dmg = int(final_dmg * res)

            unit.current_hp -= final_dmg
            context.log.append(f"💥 {unit.name} -{final_dmg} HP (x{scale})")

    # 4. Отключаем стандартный урон игры (HP), если нужно
    if prevent_standard:
        context.damage_multiplier = 0.0
        # context.log.append("(No HP Dmg)")

SCRIPTS_REGISTRY = {
    "apply_status": apply_status,
    "restore_hp": restore_hp,
    "steal_status": steal_status,
    "multiply_status": multiply_status,
}