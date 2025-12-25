# logic/passives.py
from logic.context import RollContext
from core.models import DiceType


class BasePassive:
    id = "base"
    name = "Base Passive"
    description = ""

    # Те же хуки, что и у статусов
    def on_combat_start(self, unit, log_func): pass

    def on_combat_end(self, unit, log_func): pass

    def on_round_start(self, unit, log_func): pass

    def on_round_end(self, unit, log_func): pass

    def on_roll(self, ctx: RollContext): pass

    def on_clash_win(self, ctx: RollContext): pass

    def on_clash_lose(self, ctx: RollContext): pass

    def on_hit(self, ctx: RollContext): pass


# --- ТАЛАНТ: СИЛА ЗА БОЛЬ ---
class TalentPainToPower(BasePassive):
    id = "pain_to_power"
    name = "Blood Boil"
    description = "Gain 1 Strength next turn for every 10 HP lost."

    def on_round_end(self, unit, log_func):
        # 1. Считаем, сколько полных десятков ХП потеряно
        lost_hp = unit.max_hp - unit.current_hp
        chunks = lost_hp // 10

        # 2. Смотрим, сколько мы уже "оплатили" ранее
        # Ключ в памяти уникален для этого таланта
        mem_key = f"{self.id}_chunks"
        previous_chunks = unit.memory.get(mem_key, 0)

        # 3. Вычисляем разницу
        diff = chunks - previous_chunks

        if diff > 0:
            unit.add_status("strength", diff, duration=2, delay=0)

            # Запоминаем новый уровень боли
            unit.memory[mem_key] = chunks

            if log_func:
                log_func(f"🩸 {self.name}: Lost {diff * 10} HP -> +{diff} Str next turn")


# --- ПАССИВКА: ОДИНОКИЙ ФИКСЕР (Пример) ---
class PassiveLoneFixer(BasePassive):
    id = "lone_fixer"
    name = "Lone Fixer"

    def on_roll(self, ctx: RollContext):
        # В оригинале: +3 силы если нет союзников. Тут упростим: всегда +1
        ctx.modify_power(1, "Lone Fixer")


# --- РЕЕСТР ---
PASSIVE_REGISTRY = {
    "pain_to_power": TalentPainToPower(),
    "lone_fixer": PassiveLoneFixer(),
}