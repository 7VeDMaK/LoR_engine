import random
from typing import Dict, List, Tuple, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.unit import Unit


class UnitStatusMixin:
    """
    Отвечает только за хранение и модификацию статус-эффектов (Strength, Bleed и т.д.).
    """

    def _ensure_status_storage(self):
        if not hasattr(self, "_status_effects"): self._status_effects = {}
        if not hasattr(self, "delayed_queue"): self.delayed_queue = []

    @property
    def statuses(self) -> Dict[str, int]:
        self._ensure_status_storage()
        summary = {}
        for name, instances in self._status_effects.items():
            total = sum(i["amount"] for i in instances)
            if total > 0:
                summary[name] = total
        return summary

    def add_status(self, name: str, amount: int, duration: int = 1, delay: int = 0):
        self._ensure_status_storage()
        if amount <= 0: return

        if delay > 0:
            self.delayed_queue.append({
                "name": name, "amount": amount, "duration": duration, "delay": delay
            })
            return

        if name not in self._status_effects:
            self._status_effects[name] = []

        self._status_effects[name].append({"amount": amount, "duration": duration})

    def get_status(self, name: str) -> int:
        self._ensure_status_storage()
        if name not in self._status_effects: return 0
        return sum(i["amount"] for i in self._status_effects[name])

    def remove_status(self, name: str, amount: int = None):
        self._ensure_status_storage()
        if name not in self._status_effects: return

        if amount is None:
            del self._status_effects[name]
            return

        # Удаляем, начиная с самых коротких по длительности
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


class UnitCombatMixin:
    """
    Боевая логика: броски инициативы, проверки состояния (смерть, стаггер).
    """

    def roll_speed_dice(self):
        """Генерация активных слотов на раунд."""
        self.active_slots = []

        if self.is_dead():
            return

        # 1. Основные кубики (расчитанные из статов)
        for (d_min, d_max) in self.computed_speed_dice:
            mod = self.get_status("haste") - self.get_status("slow") - self.get_status("bind")
            val = max(1, random.randint(d_min, d_max) + mod)
            self.active_slots.append({
                'speed': val, 'card': None, 'target_slot': None, 'is_aggro': False
            })

        # 2. Активные способности (Ярость)
        # Если есть бафф ярости, добавляем кубик, копирующий статы ПЕРВОГО кубика
        if self.active_buffs.get("berserker_rage", 0) > 0:
            if self.computed_speed_dice:
                d_min, d_max = self.computed_speed_dice[0]
            else:
                d_min, d_max = self.base_speed_min, self.base_speed_max

            mod = self.get_status("haste") - self.get_status("slow") - self.get_status("bind")
            val = max(1, random.randint(d_min, d_max) + mod)

            self.active_slots.append({
                'speed': val, 'card': None, 'target_slot': None, 'is_aggro': False,
                'source_effect': 'Rage 😡'
            })

    def is_staggered(self) -> bool:
        return self.current_stagger <= 0

    def is_dead(self) -> bool:
        return self.current_hp <= 0


class UnitLifecycleMixin:
    """
    Управление ресурсами (HP, SP) и временем (кулдауны).
    """

    def heal_hp(self, amount: int, source_unit=None) -> int:
        """
        Восстанавливает HP.
        source_unit: кто лечит (None или self = самолечение).
        """
        eff = 1.0 + self.modifiers.get("heal_efficiency", 0.0)

        # --- ЛОГИКА "ДОЧЬ ПЕРЕУЛКА" ---
        # Если лечит КТО-ТО ДРУГОЙ, эффективность режется
        if source_unit and source_unit != self:
            if "daughter_of_backstreets" in self.passives:
                eff *= 0.5
                # (Опционально можно добавить лог, но mixin не имеет доступа к логгеру боя)

        final_amt = int(amount * eff)

        # Deep Wound режет хил
        if self.get_status("deep_wound") > 0:
            final_amt = int(final_amt * 0.75)
            self.remove_status("deep_wound", 1)

        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + final_amt)
        return self.current_hp - old_hp

    def take_sanity_damage(self, amount: int):
        self.current_sp = max(-45, self.current_sp - amount)

    def tick_cooldowns(self):
        for k in list(self.cooldowns.keys()):
            self.cooldowns[k] -= 1
            if self.cooldowns[k] <= 0: del self.cooldowns[k]

        for k in list(self.active_buffs.keys()):
            self.active_buffs[k] -= 1
            if self.active_buffs[k] <= 0: del self.active_buffs[k]

        if self.is_dead(): self.active_buffs.clear()