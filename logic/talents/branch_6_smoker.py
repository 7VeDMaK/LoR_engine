from logic.passives.base_passive import BasePassive

# ==========================================
# 6.1 Скрываюсь в дыму (Hiding in Smoke)
# ==========================================
class TalentHidingInSmoke(BasePassive):
    id = "hiding_in_smoke"
    name = "Скрываюсь в дыму"
    description = "Дым теперь повышает сопротивление урону (до 30%), а не увеличивает входящий урон."


# ==========================================
# 6.2 Универсальность дыма (Smoke Universality)
# ==========================================
class TalentSmokeUniversality(BasePassive):
    id = "smoke_universality"
    name = "Универсальность дыма"
    description = "Активно: Конвертируйте Дым в баффы (Сила, Скорость, Стойкость, Самообладание, Защита)."
    is_active_ability = True

    # Опции для выпадающего списка в UI
    # Format: "Label": {"cost": int, "effect": "status_id", "amt": int}
    conversion_options = {
        "4 Smoke -> 1 Strength": {"cost": 4, "stat": "strength", "amt": 1},
        "3 Smoke -> 1 Haste": {"cost": 3, "stat": "haste", "amt": 1},
        "4 Smoke -> 1 Endurance": {"cost": 4, "stat": "endurance", "amt": 1},
        "3 Smoke -> 5 Self-Control": {"cost": 3, "stat": "self_control", "amt": 5},
        "3 Smoke -> 1 Protection": {"cost": 3, "stat": "protection", "amt": 1},
    }

    def activate(self, unit, log_func, choice_key=None):
        """
        choice_key: Строка-ключ из conversion_options (например, "4 Smoke -> 1 Strength")
        """
        if not choice_key or choice_key not in self.conversion_options:
            if log_func: log_func("⚠️ Ошибка: Не выбрана опция конвертации.")
            return False

        opt = self.conversion_options[choice_key]
        cost = opt["cost"]
        target_stat = opt["stat"]
        amount = opt["amt"]

        current_smoke = unit.get_status("smoke")

        if current_smoke < cost:
            if log_func: log_func(f"❌ Недостаточно Дыма! (Нужно {cost}, есть {current_smoke})")
            return False

        # Списываем дым
        unit.remove_status("smoke", cost)

        # Начисляем бонус
        unit.add_status(target_stat, amount)

        if log_func:
            log_func(f"🌫️➡️✨ **{self.name}**: Потрачено {cost} Дыма -> Получено +{amount} {target_stat.capitalize()}!")

        return True


class TalentFrenzy(BasePassive):
    id = "frenzy"
    name = "Неистовство"
    description = "5.5 Пассивно: Дает доп. слот с фиксированной атакой (5-7). Если Самообладание > 10, дает еще один слот (6-8)."
    # Логика теперь перенесена в UnitCombatMixin, как у Ярости