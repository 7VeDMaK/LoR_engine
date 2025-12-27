# core/unit_mixins.py
import random
from typing import Dict, List, Tuple, Any, TYPE_CHECKING
from core.enums import DiceType
# Импортируем классы для создания карт на лету
from core.card import Card
from core.dice import Dice

if TYPE_CHECKING:
    from core.unit import Unit


class UnitStatusMixin:
    # ... (код без изменений) ...
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
    Боевая логика: броски инициативы, проверки состояния.
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

        # 2. Активные способности (Ярость - Berserker Rage)
        if self.active_buffs.get("berserker_rage", 0) > 0:
            d_min, d_max = self.computed_speed_dice[0] if self.computed_speed_dice else (self.base_speed_min,
                                                                                         self.base_speed_max)
            mod = self.get_status("haste") - self.get_status("slow") - self.get_status("bind")
            val = max(1, random.randint(d_min, d_max) + mod)

            self.active_slots.append({
                'speed': val, 'card': None, 'target_slot': None, 'is_aggro': False,
                'source_effect': 'Rage 😡'
            })

        # 3. ТАЛАНТ: НЕИСТОВСТВО (Frenzy) - ИСПРАВЛЕННОЕ СКАЛИРОВАНИЕ
        if "frenzy" in self.talents:
            # === ИСПРАВЛЕНИЕ: Берем сильнейший кубик, как в Ярости ===
            if self.computed_speed_dice:
                d_min, d_max = self.computed_speed_dice[0]
            else:
                d_min, d_max = self.base_speed_min, self.base_speed_max
            # ========================================================

            mod = self.get_status("haste") - self.get_status("slow") - self.get_status("bind")

            # --- Слот 1: Контр-кубик (5-7) ---
            val1 = max(1, random.randint(d_min, d_max) + mod)

            card_frenzy_1 = Card(
                id="frenzy_counter_1", name="Counter (5-7)", tier=1, card_type="melee",
                description="Counter Die: Перехватывает односторонние атаки.",
                dice_list=[Dice(5, 7, DiceType.SLASH, is_counter=True)]
            )

            self.active_slots.append({
                'speed': val1,
                'card': card_frenzy_1,
                'target_slot': None,
                'is_aggro': False,
                'source_effect': 'Counter ⚡',
                'locked': True
            })

            # --- Слот 2: Если Self-Control > 10 (6-8) ---
            if self.get_status("self_control") > 10:
                val2 = max(1, random.randint(d_min, d_max) + mod)

                card_frenzy_2 = Card(
                    id="frenzy_counter_2", name="Counter II (6-8)", tier=2, card_type="melee",
                    description="Counter Die: Перехватывает односторонние атаки.",
                    dice_list=[Dice(6, 8, DiceType.SLASH, is_counter=True)]
                )

                self.active_slots.append({
                    'speed': val2,
                    'card': card_frenzy_2,
                    'target_slot': None,
                    'is_aggro': False,
                    'source_effect': 'Counter+ ⚡',
                    'locked': True
                })

        if self.get_status("red_lycoris") > 0:
            for slot in self.active_slots:
                slot['prevent_redirection'] = True
                # Визуальная пометка для игрока
                if not slot.get('source_effect'):
                    slot['source_effect'] = "Lycoris 🩸"

        # === ТАЛАНТ: МАХНУТЬ ХВОСТИКОМ (Tail Swipe) ===
        if "wag_tail" in self.passives:
            # Берем значения скорости как для основного кубика
            if self.computed_speed_dice:
                d_min, d_max = self.computed_speed_dice[0]
            else:
                d_min, d_max = self.base_speed_min, self.base_speed_max

            mod = self.get_status("haste") - self.get_status("slow") - self.get_status("bind")
            val_tail = max(1, random.randint(d_min, d_max) + mod)

            # Создаем техническую карту с контр-кубиком (Уклонение 5-7)
            card_tail = Card(
                id="tail_swipe_counter",
                name="Tail Counter",
                description="Counter Evade: Отражает атаку и сгорает.",
                dice_list=[Dice(5, 7, DiceType.EVADE, is_counter=True)]
            )

            # Добавляем отдельный слот
            self.active_slots.append({
                'speed': val_tail,
                'card': card_tail,
                'target_slot': -1,
                'is_aggro': False,
                'source_effect': 'Tail Swipe 🐈',
                'locked': True,  # Запрещаем менять карту в симуляторе
                'consumed': False
            })

    def is_staggered(self) -> bool:
        if self.get_status("red_lycoris") > 0:
            return False
        return self.current_stagger <= 0

    def is_dead(self) -> bool:
        if self.get_status("red_lycoris") > 0:
            return False

        return self.current_hp <= 0


class UnitLifecycleMixin:
    # ... (без изменений, скопируйте из оригинального файла или оставьте как есть)
    def heal_hp(self, amount: int) -> int:
        eff = 1.0 + self.modifiers.get("heal_efficiency", 0.0)
        final_amt = int(amount * eff)
        if self.get_status("deep_wound") > 0:
            final_amt = int(final_amt * 0.75)
            self.remove_status("deep_wound", 1)
        self.current_hp = min(self.max_hp, self.current_hp + final_amt)
        return final_amt

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