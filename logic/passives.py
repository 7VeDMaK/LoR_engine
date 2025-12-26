# logic/passives.py
from logic.context import RollContext
from core.models import DiceType


class BasePassive:
    id = "base"
    name = "Base Passive"
    description = "No description"

    # Флаги для активных способностей
    is_active_ability = False
    cooldown = 0
    duration = 0

    # Хуки событий
    def on_combat_start(self, unit, log_func): pass

    def on_combat_end(self, unit, log_func): pass

    def on_round_start(self, unit, log_func): pass

    def on_round_end(self, unit, log_func): pass

    def on_roll(self, ctx: RollContext): pass

    def on_clash_win(self, ctx: RollContext): pass

    def on_clash_lose(self, ctx: RollContext): pass

    def on_hit(self, ctx: RollContext): pass

    # Новый метод для кнопки активации
    def activate(self, unit, log_func): pass


# ==========================================
# 5.1 Встроенная Броня (Naked Defense)
# ==========================================
class TalentNakedDefense(BasePassive):
    id = "naked_defense"
    name = "Встроенная Броня"
    description = "5.1 Если броня не надета (None), резисты становятся равными 1.0."

    def on_combat_start(self, unit, log_func):
        # Проверяем, если имя брони пустое или "None"
        if not unit.armor_name or unit.armor_name.lower() in ["none", "нет", "empty", "naked"]:
            unit.hp_resists.slash = 1.0
            unit.hp_resists.pierce = 1.0
            unit.hp_resists.blunt = 1.0
            if log_func:
                log_func(f"🛡️ {self.name}: Броня не обнаружена. Резисты установлены на 1.0")


# ==========================================
# 5.2 Злобная расплата (Vicious Payback)
# ==========================================
class TalentVengefulPayback(BasePassive):
    id = "vengeful_payback"
    name = "Злобная расплата"
    description = "5.2 За каждые 10 потерянных HP вы получаете 1 Силу на следующий раунд."

    def on_round_end(self, unit, log_func):
        # 1. Считаем потерянные HP
        lost_hp = unit.max_hp - unit.current_hp
        chunks = lost_hp // 10

        # 2. Смотрим память (сколько мы уже учли)
        mem_key = f"{self.id}_chunks"
        previous_chunks = unit.memory.get(mem_key, 0)

        if chunks > previous_chunks:
            diff = chunks - previous_chunks
            unit.add_status("strength", diff, duration=2)  # Duration 2, чтобы хватило на некст раунд
            if log_func:
                log_func(f"🩸 {self.name}: Потеряно здоровья (стаков: {diff}). +{diff} Силы.")

        # Обновляем память
        unit.memory[mem_key] = chunks


# ==========================================
# 5.3 Ярость (Berserker Rage)
# ==========================================
class TalentBerserkerRage(BasePassive):
    id = "berserker_rage"
    name = "Ярость"
    description = "5.3 Активно: Входите в ярость на 3 раунда (+1 Слот Атаки). КД 5 ходов. Спадает при потере сознания."

    is_active_ability = True
    cooldown = 5
    duration = 3

    def activate(self, unit, log_func):
        # Проверка КД
        if unit.cooldowns.get(self.id, 0) > 0:
            return False

        # Активация
        unit.active_buffs[self.id] = self.duration
        unit.cooldowns[self.id] = self.cooldown

        if log_func:
            log_func(f"😡 {self.name}: Активирована! (+1 Куб Атаки на 3 раунда)")
        return True


# ==========================================
# 5.4 Не теряя голову (Composure / Calm Mind)
# ==========================================
class TalentCalmMind(BasePassive):
    id = "calm_mind"
    name = "Не теряя голову"
    description = "5.4 Все атаки восстанавливают 1 SP (Самообладание)."

    def on_hit(self, ctx: RollContext):
        # Восстанавливаем 1 SP
        unit = ctx.source
        if unit.current_sp < unit.max_sp:
            unit.current_sp += 1
            ctx.log.append(f"🧠 {self.name}: +1 SP")


# --- РЕЕСТР (Все доступные пассивки должны быть здесь) ---
PASSIVE_REGISTRY = {
    "naked_defense": TalentNakedDefense(),
    "vengeful_payback": TalentVengefulPayback(),
    "berserker_rage": TalentBerserkerRage(),
    "calm_mind": TalentCalmMind(),
}