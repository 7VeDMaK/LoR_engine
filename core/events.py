import heapq
from collections import defaultdict

class EventManager:
    def __init__(self):
        self.listeners = defaultdict(list)

    def subscribe(self, event_type, callback, priority=100):
        # priority: меньше = раньше срабатывает
        heapq.heappush(self.listeners[event_type], (priority, callback))

    def emit(self, event_type, context):
        if event_type in self.listeners:
            # Создаем копию списка, чтобы избежать проблем если во время итерации кто-то отпишется
            # (хотя heapq неудобно копировать, здесь упростим перебором)
            sorted_listeners = sorted(self.listeners[event_type], key=lambda x: x[0])
            for _, callback in sorted_listeners:
                callback(context)
        return context