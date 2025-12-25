from typing import List
from logic.status_definitions import STATUS_REGISTRY

class StatusManager:
    @staticmethod
    def process_turn_end(unit: 'Unit') -> List[str]:
        logs = []
        # Копия ключей, так как статусы могут удаляться внутри цикла
        current_statuses = list(unit.statuses.items())

        for status_id, stack in current_statuses:
            if status_id in STATUS_REGISTRY:
                handler = STATUS_REGISTRY[status_id]
                msgs = handler.on_turn_end(unit, stack)
                logs.extend(msgs)
            else:
                # Fallback для статусов, которых нет в реестре (например временные заглушки)
                pass

        return logs