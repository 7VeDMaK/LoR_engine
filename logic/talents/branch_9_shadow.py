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