from logic.passives.base_passive import BasePassive

# ==========================================
# 1.1 Держать себя в руках
# ==========================================
class TalentKeepItTogether(BasePassive):
    id = "keep_it_together"
    name = "Держать себя в руках"
    description = "1.1 Ваш Макс. Рассудок увеличивается на 20%."
    is_active_ability = False

    def on_calculate_stats(self, unit) -> dict:
        # Возвращаем модификатор +20% к SP
        # (Ключ max_sp_pct мы сейчас обработаем в calculations.py)
        return {"max_sp_pct": 20}


# ==========================================
# 1.2 Центр у равновесия
# ==========================================
class TalentCenterOfBalance(BasePassive):
    id = "center_of_balance"
    name = "Центр у равновесия"
    description = "1.2 В начале раунда восстанавливает 2 + (Макс. SP / 20) рассудка."
    is_active_ability = False

    def on_combat_start(self, unit, log_func, **kwargs):
        # Формула: 2 + (Макс СП / 20)
        # // - это целочисленное деление (округляет вниз)
        bonus_from_max = unit.max_sp // 20
        heal_amount = 2 + bonus_from_max

        # Восстанавливаем SP, но не выше максимума
        old_sp = unit.current_sp
        unit.current_sp = min(unit.max_sp, unit.current_sp + heal_amount)

        actual_heal = unit.current_sp - old_sp

        # Пишем в лог, только если реально что-то восстановили
        if log_func and actual_heal > 0:
            log_func(f"🧠 {self.name}: Восстановлено {actual_heal} SP (2 + {bonus_from_max})")