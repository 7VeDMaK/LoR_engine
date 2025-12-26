from typing import Dict, List


class UnitStatusMixin:
    """
    Миксин, отвечающий за управление статусами и эффектами юнита.
    Ожидает наличие self._status_effects и self.delayed_queue в основном классе.
    """

    @property
    def statuses(self) -> Dict[str, int]:
        summary = {}
        # self._status_effects должен быть определен в Unit
        for name, instances in self._status_effects.items():
            if sum(i["amount"] for i in instances) > 0:
                summary[name] = sum(i["amount"] for i in instances)
        return summary

    def add_status(self, name: str, amount: int, duration: int = 1, delay: int = 0):
        if amount <= 0: return

        if delay > 0:
            self.delayed_queue.append({
                "name": name,
                "amount": amount,
                "duration": duration,
                "delay": delay
            })
            return

        if name not in self._status_effects:
            self._status_effects[name] = []

        if amount > 0:
            self._status_effects[name].append({"amount": amount, "duration": duration})

    def get_status(self, name: str) -> int:
        if name not in self._status_effects: return 0
        return sum(i["amount"] for i in self._status_effects[name])

    def remove_status(self, name: str, amount: int = None):
        if name not in self._status_effects: return

        if amount is None:
            del self._status_effects[name]
            return

        items = sorted(self._status_effects[name], key=lambda x: x["duration"])
        rem = amount
        new_items = []

        for item in items:
            if rem <= 0:
                new_items.append(item)
                continue

            if item["amount"] > rem:
                item["amount"] -= rem
                rem = 0
                new_items.append(item)
            else:
                rem -= item["amount"]

        if not new_items:
            del self._status_effects[name]
        else:
            self._status_effects[name] = new_items