# logic/talents/definitions.py
from logic.passives import BasePassive
from logic.context import RollContext
from core.enums import DiceType

# ==========================================
# 5.1 Встроенная Броня
# ==========================================
class TalentNakedDefense(BasePassive):
    id = "naked_defense"
    name = "Встроенная Броня"
    description = "5.1 Если броня не надета (None), резисты становятся равными 1.0."

    def on_combat_start(self, unit, log_func):
        if not unit.armor_name or unit.armor_name.lower() in ["none", "нет", "empty", "naked"]:
            unit.hp_resists.slash = 1.0
            unit.hp_resists.pierce = 1.0
            unit.hp_resists.blunt = 1.0
            if log_func:
                log_func(f"🛡️ {self.name}: Броня не обнаружена. Резисты установлены на 1.0")


# ==========================================
# 5.2 Злобная расплата
# ==========================================
class TalentVengefulPayback(BasePassive):
    id = "vengeful_payback"
    name = "Злобная расплата"
    description = "5.2 За каждые 10 потерянных HP вы получаете 1 Силу на следующий раунд."

    def on_round_end(self, unit, log_func):
        lost_hp = unit.max_hp - unit.current_hp
        chunks = lost_hp // 10
        mem_key = f"{self.id}_chunks"
        previous_chunks = unit.memory.get(mem_key, 0)

        if chunks > previous_chunks:
            diff = chunks - previous_chunks
            unit.add_status("strength", diff, duration=2)
            if log_func:
                log_func(f"🩸 {self.name}: Потеряно здоровья (стаков: {diff}). +{diff} Силы.")
        unit.memory[mem_key] = chunks


# ==========================================
# 5.3 Ярость
# ==========================================
class TalentBerserkerRage(BasePassive):
    id = "berserker_rage"
    name = "Ярость"
    description = "5.3 Активно: Входите в ярость на 3 раунда (+1 Слот Атаки). КД 5 ходов."
    is_active_ability = True
    cooldown = 5
    duration = 3

    def activate(self, unit, log_func):
        if unit.cooldowns.get(self.id, 0) > 0: return False
        unit.active_buffs[self.id] = self.duration
        unit.cooldowns[self.id] = self.cooldown
        if log_func:
            log_func(f"😡 {self.name}: Активирована! (+1 Куб Атаки)")
        return True


# ==========================================
# 5.4 Не теряя голову (Calm Mind)
# ==========================================
class TalentCalmMind(BasePassive):
    id = "calm_mind"
    name = "Не теряя голову"
    description = "5.4 При атаке накладывает +1 Самообладание (Макс 100). Самообладание дает шанс крита (x2 урон)."

    def on_hit(self, ctx: RollContext):
        # Проверяем текущее кол-во стаков
        current_stacks = ctx.source.get_status("self_control")

        # Максимум 100 зарядов
        if current_stacks < 100:
            ctx.source.add_status("self_control", 1)
            ctx.log.append(f"💨 {self.name}: +1 Self-Control")

            # ==========================================
            # 6.1 Скрываюсь в дыму (Hiding in Smoke)
            # ==========================================
class TalentHidingInSmoke(BasePassive):
    id = "hiding_in_smoke"
    name = "Скрываюсь в дыму"
    description = "Дым теперь повышает сопротивление урону (до 30%), а не увеличивает входящий урон."