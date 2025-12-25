from logic.context import RollContext
from logic.status_definitions import STATUS_REGISTRY

class ModifierSystem:
    @staticmethod
    def apply_modifiers(context: RollContext):
        unit = context.source

        # Перебираем все статусы юнита
        # Мы делаем list(items), чтобы можно было безопасно менять словарь, если вдруг понадобится
        for status_id, stack in list(unit.statuses.items()):
            if status_id in STATUS_REGISTRY:
                handler = STATUS_REGISTRY[status_id]
                handler.modify_roll(context, stack)

        return context