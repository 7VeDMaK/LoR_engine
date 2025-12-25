# logic/passives.py
from logic.context import RollContext
from core.models import DiceType


class BasePassive:
    id = "base"
    name = "Base Passive"
    description = "No description"

    # Хуки событий
    def on_combat_start(self, unit, log_func): pass

    def on_combat_end(self, unit, log_func): pass

    def on_round_start(self, unit, log_func): pass

    def on_round_end(self, unit, log_func): pass

    def on_roll(self, ctx: RollContext): pass

    def on_clash_win(self, ctx: RollContext): pass

    def on_clash_lose(self, ctx: RollContext): pass

    def on_hit(self, ctx: RollContext): pass


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

        # 3. Разница (новые потери здоровья)
        # В оригинале: "За каждые 10 хп... срабатывает 1 раз".
        # Значит, если здоровье упало с 100 до 80, мы получаем 2 силы.
        # Если потом вылечились и снова упали, сработает ли снова? Обычно в таких системах считают пороги.
        # Реализуем так: если текущее кол-во чанков больше предыдущего -> даем бафф

        if chunks > previous_chunks:
            diff = chunks - previous_chunks
            unit.add_status("strength", diff, duration=2)  # Duration 2, чтобы хватило на некст раунд
            if log_func:
                log_func(f"🩸 {self.name}: Потеряно здоровья (стаков: {diff}). +{diff} Силы.")

        # Обновляем память (если вылечились, chunks уменьшится, и мы сможем получить бонус снова при получении урона)
        unit.memory[mem_key] = chunks


# ==========================================
# 5.3 Ярость (Berserker Rage)
# ==========================================
class TalentBerserkerRage(BasePassive):
    id = "berserker_rage"
    name = "Ярость"
    description = "5.3 Активно: Входите в ярость на 3 раунда. (Здесь: Авто-активация при старте). Дает мощь и скорость."

    def on_combat_start(self, unit, log_func):
        # В симуляторе нет кнопок "Активно", поэтому активируем при старте боя
        # Или можно сделать шанс. Сделаем 100% при старте для теста.
        unit.add_status("strength", 1, duration=3)
        unit.add_status("haste", 2, duration=3)  # Скорость
        if log_func:
            log_func(f"😡 {self.name}: Активирована! (+Сила, +Скорость на 3 хода)")


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
    # Старые (из примера)
    "lone_fixer": BasePassive(),  # Заглушка, если нужна

    # Берсерк (из картинки)
    "naked_defense": TalentNakedDefense(),
    "vengeful_payback": TalentVengefulPayback(),
    "berserker_rage": TalentBerserkerRage(),
    "calm_mind": TalentCalmMind(),
}