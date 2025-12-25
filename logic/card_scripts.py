# logic/card_scripts.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logic.modifiers import RollContext


def apply_status(context: 'RollContext', params: dict):
    status_name = params.get("status")
    stack = params.get("stack", 1)
    target_type = params.get("target", "target")

    # Читаем новые параметры
    duration = int(params.get("duration", 1))
    delay = int(params.get("delay", 0))

    unit_to_affect = context.target if target_type == "target" else context.source
    if not unit_to_affect: return

    if unit_to_affect and status_name:
        unit_to_affect.add_status(status_name, stack, duration=duration, delay=delay)

        # Формируем красивый лог
        extras = []
        if duration > 1: extras.append(f"{duration} turns")
        if delay > 0: extras.append(f"in {delay} turns")
        extra_str = f" ({', '.join(extras)})" if extras else ""

        context.log.append(f"🧪 {status_name.capitalize()} +{stack}{extra_str} to {unit_to_affect.name}")


def restore_hp(context: 'RollContext', params: dict):
    amount = params.get("amount", 0)
    target_type = params.get("target", "self")
    unit = context.source if target_type == "self" else context.target
    if unit:
        actual_heal = unit.heal_hp(amount)
        context.log.append(f"💚 Healed {actual_heal} HP ({unit.name})")


SCRIPTS_REGISTRY = {
    "apply_status": apply_status,
    "restore_hp": restore_hp
}