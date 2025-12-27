# logic/card_scripts.py
from typing import TYPE_CHECKING
from core.enums import DiceType

if TYPE_CHECKING:
    from logic.modifiers import RollContext


# Вспомогательная функция для иконок
def _get_icon(unit, context):
    return "👤" if unit == context.source else "🎯"


def apply_status(context: 'RollContext', params: dict):
    status_name = params.get("status")
    stack = params.get("stack", 1)
    target_type = params.get("target", "target")
    duration = int(params.get("duration", 1))

    # Хак для Дыма
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

        # Красивый лог
        icon = _get_icon(unit, context)
        context.log.append(f"{icon} **{status_name.capitalize()}** +{stack}")


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

        context.log.append(f"✋ **Steal**: Stole {amount} {status_name} from 🎯 → 👤")


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
        icon = _get_icon(unit, context)
        context.log.append(f"✖️ **Multiply**: {status_name} x{multiplier} ({current} → {current + add}) on {icon}")


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
            context.log.append(f"😵 **{unit.name}**: -{base} Stagger (Custom)")
        elif dmg_type == "hp":
            unit.current_hp -= base
            context.log.append(f"💥 **{unit.name}**: -{base} HP (Custom)")

    if prevent_std:
        context.damage_multiplier = 0.0


def restore_hp(context: 'RollContext', params: dict):
    amount = params.get("amount", 0)
    target_type = params.get("target", "self")
    unit = context.source if target_type == "self" else context.target

    if unit:
        heal = unit.heal_hp(amount)
        icon = _get_icon(unit, context)
        context.log.append(f"💚 {icon} **Heal** +{heal} HP")


SCRIPTS_REGISTRY = {
    "apply_status": apply_status,
    "restore_hp": restore_hp,
    "steal_status": steal_status,
    "multiply_status": multiply_status,
    "deal_custom_damage": deal_custom_damage
}