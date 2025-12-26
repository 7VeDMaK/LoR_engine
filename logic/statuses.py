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
            # Проверка на случай, если статус был удален ранее
            if status_id not in unit._status_effects:
                continue

            # Получаем текущие данные для расчета стаков
            # Важно: пока не сохраняем ссылку для изменения, только для чтения суммы
            instances_start = unit._status_effects[status_id]
            total_stack = sum(i["amount"] for i in instances_start)

            # 1. Вызываем логику статуса (Strength, Bleed, SelfControl и т.д.)
            # Этот вызов может изменить unit._status_effects (например, удалить стаки)
            if status_id in STATUS_REGISTRY and total_stack > 0:
                handler = STATUS_REGISTRY[status_id]
                msgs = handler.on_turn_end(unit, total_stack)
                logs.extend(msgs)

            # 2. ПРОВЕРЯЕМ, СУЩЕСТВУЕТ ЛИ СТАТУС ПОСЛЕ ОБРАБОТЧИКА
            if status_id not in unit._status_effects:
                # Если on_turn_end удалил статус полностью (стаки <= 0),
                # то нам не нужно уменьшать длительность или удалять его снова.
                continue

            # 3. БЕРЕМ АКТУАЛЬНЫЙ СПИСОК (Re-fetch)
            # Это критически важно: если handler изменил список (remove_status),
            # мы должны работать с НОВЫМ списком, иначе мы отменим изменения стаков.
            current_instances = unit._status_effects[status_id]

            next_instances = []

            # 4. Уменьшаем Duration каждого отдельного наложения
            for item in current_instances:
                item["duration"] -= 1
                # Оставляем только те, у которых еще есть время
                if item["duration"] > 0:
                    next_instances.append(item)
                # else: expired

            # 5. Обновляем список на юните или удаляем ключ
            if next_instances:
                unit._status_effects[status_id] = next_instances
            else:
                # Безопасное удаление (мы уже проверили наличие ключа выше,
                # и мы единственные, кто трогает его в этом блоке)
                del unit._status_effects[status_id]

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