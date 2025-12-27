from core.enums import DiceType
from logic.context import RollContext
from logic.passives.base_passive import BasePassive


# ==========================================
# 9.1 Б Месть (Revenge)
# ==========================================
class TalentRevenge(BasePassive):
    id = "revenge"
    name = "Месть"
    description = "9.1 При получении урона: Следующая успешная атака наносит x1.5 урона."
    is_active_ability = False

    def on_take_damage(self, unit, amount: int, dmg_type: str, log_func=None):
        # Активируется при любом полученном уроне > 0
        if amount > 0:
            # Накладываем метку (стак 1, длительность бесконечная пока не потратим)
            unit.add_status("revenge_buff", 1, duration=99)
            if log_func:
                log_func(f"🩸 {self.name}: Урон получен! Месть готова.")

    def on_hit(self, ctx: RollContext):
        # Проверяем, есть ли заряд мести
        if ctx.source.get_status("revenge_buff") > 0:
            # Применяем x1.5
            ctx.damage_multiplier *= 1.5

            # Тратим заряд (все стаки, чтобы не стакалось бесконечно, или 1 - по желанию)
            # По условию "Следующий куб", значит тратим всё сразу на один удар
            ctx.source.remove_status("revenge_buff")

            ctx.log.append(f"⚔️ {self.name}: CRITICAL VENGEANCE (x1.5 Dmg)!")

# ==========================================
# 9.2 А Не превеликое внимание
# ==========================================
class TalentNotGreatAttention(BasePassive):
    id = "not_great_attention"
    name = "Не превеликое внимание"
    description = "9.2 А Пассивно: +10 к Акробатике."
    is_active_ability = False

    def on_calculate_stats(self, unit) -> dict:
        # Просто возвращаем бонус к навыку
        return {"acrobatics": 10}


# ==========================================
# 9.3 Б Резня (Slaughter)
# ==========================================
class TalentSlaughter(BasePassive):
    id = "slaughter"
    name = "Резня"
    description = "9.3 Б: Последний куб (Slash/Pierce) накладывает Кровотечение 2+(Lvl/10)."
    is_active_ability = False

    def on_hit(self, ctx: RollContext):
        # 1. Проверяем тип урона (Slash или Pierce)
        if ctx.dice.dtype not in [DiceType.SLASH, DiceType.PIERCE]:
            return

        # 2. Получаем карту и проверяем, последний ли это кубик
        card = ctx.source.current_card
        if not card or not card.dice_list:
            return

        # Сравниваем текущий кубик (ctx.dice) с последним кубиком в списке карты
        last_die = card.dice_list[-1]

        # Оператор 'is' проверяет, является ли это тем же самым объектом в памяти
        if ctx.dice is last_die:
            # 3. Считаем стаки
            lvl = ctx.source.level
            bleed_amt = 2 + (lvl // 10)

            # 4. Накладываем эффект на цель (того, кого ударили)
            # В контексте атаки ctx.target - это цель (если удар был не по своей воле, это может быть None, но обычно есть)
            target = ctx.target
            if target:
                target.add_status("bleed", bleed_amt, duration=3)  # Длительность bleed стандартно убывает сама
                ctx.log.append(f"🩸 {self.name}: Последний куб -> +{bleed_amt} Bleed")

# ==========================================
# 9.4 А Быстрый и Тихий
# ==========================================
class TalentFastAndSilent(BasePassive):
    id = "fast_and_silent"
    name = "Быстрый и Тихий"
    description = "9.4 А Пассивно: +10 к Ловкости."
    is_active_ability = False

    def on_calculate_stats(self, unit) -> dict:
        return {"agility": 10}