from logic.passives.base_passive import BasePassive


class PassiveSCells(BasePassive):
    id = "s_cells"
    name = "S-клетки"
    description = "В начале боя восстанавливает 10 HP за каждый имеющийся слот скорости."

    def on_combat_start(self, unit, log_func):
        # Считаем количество активных слотов (кубиков скорости)
        dice_count = len(unit.active_slots)

        if dice_count > 0:
            heal_amount = dice_count * 10
            actual_heal = unit.heal_hp(heal_amount)

            if log_func:
                log_func(f"🧬 {self.name}: {dice_count} слотов x 10 = Восстановлено {actual_heal} HP")

# ==========================================
# 5.6 Новое открытие [Сенсорные способности]
# ==========================================
class PassiveNewDiscovery(BasePassive):
    id = "new_discovery"
    name = "Новое открытие (Сенсоры 2%)"
    description = "Пассивно: Мудрость +10, Интеллект +2.\nАвтоматически открывает 'Тактический анализ'."
    is_active_ability = False

    # ВМЕСТО ХАРДКОДА В CALCULATIONS:
    def on_calculate_stats(self, unit) -> dict:
        return {
            "wisdom": 10,
            "bonus_intellect": 2,  # Специальный ключ для прямого бонуса к интеллекту
            "backstab_deal": 10,
            "backstab_take": -10
        }

    def on_combat_start(self, unit, log_func):
        if log_func:
            log_func(f"👁️ {self.name}: Сенсоры активны.")