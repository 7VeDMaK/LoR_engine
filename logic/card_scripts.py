# logic/card_scripts.py
from typing import TYPE_CHECKING
from core.enums import DiceType

if TYPE_CHECKING:
    from logic.context import RollContext


def apply_status(context: 'RollContext', params: dict):
    status_name = params.get("status")
    stack = params.get("stack", 1)
    target_type = params.get("target", "target")
    duration = int(params.get("duration", 1))

    # Хак для Дыма (Smoke) - он вечный
    if status_name == "smoke": duration = 99

    targets = []
    if target_type == "self":
        targets.append(context.source)
    elif target_type == "target":
        targets.append(context.target)
    elif target_type == "all":
        if context.source: targets.append(context.source)
        if context.target: targets.append(context.target)

    if not status_name: return

    for unit in targets:
        if not unit: continue
        unit.add_status(status_name, stack, duration=duration)

        # БЫЛО: 🧪 **Smoke** +1
        # СТАЛО: 🧪 **Lilit**: +1 Smoke
        context.log.append(f"🧪 **{unit.name}**: +{stack} {status_name.capitalize()}")


def steal_status(context: 'RollContext', params: dict):
    status_name = params.get("status")
    if not status_name: return
    thief, victim = context.source, context.target
    if not thief or not victim: return

    amount = victim.get_status(status_name)
    if amount > 0:
        victim.remove_status(status_name, amount)
        duration = 99 if status_name == "smoke" else 1
        thief.add_status(status_name, amount, duration=duration)

        # БЫЛО: ✋ **Steal**: 5 Smoke from 🎯 → 👤
        # СТАЛО: ✋ **Lilit** stole 5 Smoke from **Roland**
        context.log.append(f"✋ **{thief.name}** stole {amount} {status_name} from **{victim.name}**")
    else:
        # Можно добавить лог неудачи, если нужно
        pass


def multiply_status(context: 'RollContext', params: dict):
    status_name = params.get("status")
    multiplier = float(params.get("multiplier", 2.0))
    target_type = params.get("target", "target")
    unit = context.target if target_type == "target" else context.source
    if not unit: return

    current = unit.get_status(status_name)
    if current > 0:
        add = int(current * (multiplier - 1))
        duration = 99 if status_name == "smoke" else 1
        unit.add_status(status_name, add, duration=duration)

        context.log.append(f"✖️ **{unit.name}**: {status_name} x{multiplier} (+{add})")


def deal_custom_damage(context: 'RollContext', params: dict):
    dmg_type = params.get("type", "stagger")
    scale = float(params.get("scale", 1.0))
    target_mode = params.get("target", "target")
    prevent_std = params.get("prevent_standard", False)

    base = int(context.final_value * scale)
    targets = []
    if target_mode == "target":
        targets.append(context.target)
    elif target_mode == "self":
        targets.append(context.source)
    elif target_mode == "all":
        if context.source: targets.append(context.source)
        if context.target: targets.append(context.target)

    for unit in targets:
        if not unit: continue
        if dmg_type == "stagger":
            unit.current_stagger -= base
            context.log.append(f"😵 **{unit.name}**: -{base} Stagger")
        elif dmg_type == "hp":
            unit.current_hp -= base
            context.log.append(f"💥 **{unit.name}**: -{base} HP")

    if prevent_std:
        context.damage_multiplier = 0.0


def restore_hp(context: 'RollContext', params: dict):
    amount = params.get("amount", 0)
    target_type = params.get("target", "self")
    unit = context.source if target_type == "self" else context.target

    if unit:
        try:
            # Пытаемся передать source_unit, если метод обновлен
            heal = unit.heal_hp(amount, source_unit=context.source)
        except TypeError:
            # Если нет, по старинке
            heal = unit.heal_hp(amount)

        # БЫЛО: 💚 Heal +5 HP
        # СТАЛО: 💚 **Roland**: Healed +5 HP
        context.log.append(f"💚 **{unit.name}**: Healed +{heal} HP")


SCRIPTS_REGISTRY = {
    "apply_status": apply_status,
    "restore_hp": restore_hp,
    "steal_status": steal_status,
    "multiply_status": multiply_status,
    "deal_custom_damage": deal_custom_damage
}