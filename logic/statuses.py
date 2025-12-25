# logic/statuses.py
from typing import List

from logic.status_definitions import STATUS_REGISTRY


class StatusManager:
    @staticmethod
    def process_turn_end(unit: 'Unit') -> List[str]:
        logs = []

        # 1. ОБРАБОТКА АКТИВНЫХ СТАТУСОВ (Duration)
        current_statuses = list(unit.statuses.items())
        for status_id, stack in current_statuses:
            # Сначала эффекты (например, ожог)
            if status_id in STATUS_REGISTRY:
                handler = STATUS_REGISTRY[status_id]
                msgs = handler.on_turn_end(unit, stack)
                logs.extend(msgs)

            # Потом уменьшаем длительность
            # Если в durations нет записи, значит это "одноразовый" статус (1 ход)
            current_dur = unit.durations.get(status_id, 1)
            new_dur = current_dur - 1

            if new_dur <= 0:
                unit.remove_status(status_id)  # Удаляем полностью
            else:
                unit.durations[status_id] = new_dur  # Сохраняем

        # 2. ОБРАБОТКА ОТЛОЖЕННЫХ ЭФФЕКТОВ (Delay)
        if unit.delayed_queue:
            remaining_queue = []
            for item in unit.delayed_queue:
                item["delay"] -= 1
                if item["delay"] <= 0:
                    # Время пришло! Активируем.
                    name = item["name"]
                    amt = item["amount"]
                    dur = item["duration"]
                    unit.add_status(name, amt, duration=dur, delay=0)
                    logs.append(f"⏰ Delayed Effect: {name.capitalize()} +{amt} activated!")
                else:
                    remaining_queue.append(item)
            unit.delayed_queue = remaining_queue

        return logs