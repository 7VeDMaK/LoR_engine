# logic/statuses.py
from typing import List

from logic.status_definitions import STATUS_REGISTRY


class StatusManager:
    @staticmethod
    def process_turn_end(unit: 'Unit') -> List[str]:
        logs = []

        # Работаем с копией ключей, т.к. словарь может меняться
        active_ids = list(unit._status_effects.keys())

        for status_id in active_ids:
            instances = unit._status_effects[status_id]

            # 1. Считаем общую сумму для эффектов (например, общий урон от Блида)
            total_stack = sum(i["amount"] for i in instances)

            # Вызываем логику статуса (Strength, Bleed и т.д.)
            # Важно: сам статус теперь не управляет временем, это делает менеджер ниже
            if status_id in STATUS_REGISTRY and total_stack > 0:
                handler = STATUS_REGISTRY[status_id]
                msgs = handler.on_turn_end(unit, total_stack)
                logs.extend(msgs)

            # 2. Уменьшаем Duration каждого отдельного наложения
            next_instances = []
            expired_amount = 0

            for item in instances:
                item["duration"] -= 1
                # Оставляем только те, у которых еще есть время
                if item["duration"] > 0:
                    next_instances.append(item)
                else:
                    expired_amount += item["amount"]

            # 3. Обновляем список на юните
            if next_instances:
                unit._status_effects[status_id] = next_instances
            else:
                del unit._status_effects[status_id]  # Статус полностью истек
                # if expired_amount > 0:
                #     logs.append(f"{status_id.capitalize()} expired")

        # --- Обработка Delayed (без изменений) ---
        if unit.delayed_queue:
            remaining = []
            for item in unit.delayed_queue:
                item["delay"] -= 1
                if item["delay"] <= 0:
                    unit.add_status(item["name"], item["amount"], duration=item["duration"])
                    logs.append(f"⏰ {item['name'].capitalize()} activated!")
                else:
                    remaining.append(item)
            unit.delayed_queue = remaining

        return logs