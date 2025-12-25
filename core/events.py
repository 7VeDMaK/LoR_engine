# core/events.py
from collections import defaultdict
import heapq

class EventManager:
    def __init__(self):
        # Словарь: Ключ = Тип события, Значение = Список слушателей (функций)
        self.listeners = defaultdict(list)

    def subscribe(self, event_type, callback, priority=100):
        """
        priority: Меньше число = срабатывает раньше.
        Например, базовые баффы (10), потом умножители (50), потом финальные кэпы (100).
        """
        # Используем heapq, чтобы список всегда был отсортирован по приоритету
        heapq.heappush(self.listeners[event_type], (priority, callback))

    def emit(self, event_type, context):
        """
        Рассылает событие всем подписчикам.
        context: Объект с данными (кто атакует, какой кубик, текущее значение силы).
        """
        if event_type in self.listeners:
            # Берем всех слушателей по порядку приоритета
            for _, callback in self.listeners[event_type]:
                # Пассивка может изменить context прямо тут
                callback(context)
        return context