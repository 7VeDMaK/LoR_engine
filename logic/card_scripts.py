from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logic.modifiers import RollContext
    from core.models import Unit


def apply_status(context: 'RollContext', params: dict):
    """
    Накладывает статус на цель или на себя.
    params: {
        "status": "bleed",   # код статуса
        "stack": 1,          # количество
        "target": "target"   # "target" (враг) или "self" (себя)
    }
    """
    status_name = params.get("status")
    stack = params.get("stack", 1)
    target_type = params.get("target", "target")  # по умолчанию враг

    # Определяем, на кого вешать
    unit_to_affect = context.target if target_type == "target" else context.source

    if unit_to_affect and status_name:
        unit_to_affect.add_status(status_name, stack)
        context.log.append(f"🧪 {status_name.capitalize()} +{stack} to {unit_to_affect.name}")


# Реестр функций, доступных для вызова из JSON
SCRIPTS_REGISTRY = {
    "apply_status": apply_status,
}