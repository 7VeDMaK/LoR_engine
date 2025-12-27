# ==========================================
# Махнуть хвостиком (Wag Tail)
# ==========================================
from core.enums import DiceType
from logic.context import RollContext
from logic.passives.base_passive import BasePassive


class PassiveWagTail(BasePassive):
    id = "wag_tail"
    name = "Махнуть хвостиком"
    description = "🐈 (Пассивно) Каждый раунд создает дополнительный слот с Counter Evade (5-7). Отражает одну карту противника и исчезает."
    is_active_ability = False  # Убеждаемся, что это не активка


# ==========================================
# Демон переулка (Backstreet Demon)
# ==========================================
class PassiveBackstreetDemon(BasePassive):
    id = "backstreet_demon"
    name = "Демон переулка"
    description = "Сильная сторона: Уворот наносит урон. Слабая: Блок врага наносит вам урон."

    # --- СИЛЬНАЯ СТОРОНА ---
    def modify_clash_interaction(self, ctx, interaction, loser_ctx):
        if ctx.dice.dtype == DiceType.EVADE:
            enemy_roll = loser_ctx.final_value
            counter_dmg = enemy_roll // 2

            interaction["action"] = "damage"
            interaction["dmg_type"] = "hp"
            interaction["amount"] = counter_dmg
            interaction["target"] = loser_ctx.source
            interaction["is_full_attack"] = False

            # ПОДРОБНЫЙ ЛОГ
            ctx.log.append(f"😈 **{self.name}**: Успешный уворот! Враг открылся.")
            ctx.log.append(f"   ↳ Контратака на **{counter_dmg}** урона (50% от броска врага {enemy_roll})")

    # --- СЛАБАЯ СТОРОНА ---
    def modify_clash_interaction_loser(self, ctx, interaction, winner_ctx):
        """
        ctx: Лилит (Проигравшая)
        winner_ctx: Враг (Победитель)
        """
        if winner_ctx.dice.dtype == DiceType.BLOCK:
            dmg = winner_ctx.final_value // 2

            # Наносим урон
            ctx.source.current_hp = max(0, ctx.source.current_hp - dmg)

            # ПОДРОБНЫЙ ЛОГ
            # Используем emoji разбитого сердца и объясняем причину
            ctx.log.append(f"💔 **{self.name} (Слабость)**: Атака заблокирована!")
            ctx.log.append(f"   ↳ Лилит получает **{dmg}** урона от отдачи (50% от Блока {winner_ctx.final_value})")


# ==========================================
# Дочь переулка (Daughter of Backstreets)
# ==========================================
class PassiveDaughterOfBackstreets(BasePassive):
    id = "daughter_of_backstreets"
    name = "Дочь переулка"
    description = "В конце хода +1 HP/SP/Stagger. Лечение от чужих источников снижено на 50%."

    def on_round_end(self, unit, log_func):
        # Самолечение не режется, так как source=None (или self, если передать)
        # Но в методе tick/round_end мы вызываем heal_hp(1)
        # heal_hp по умолчанию считает source_unit=None как self, так что резать не будет.
        unit.heal_hp(1)

        if unit.current_sp < unit.max_sp: unit.current_sp += 1
        if unit.current_stagger < unit.max_stagger: unit.current_stagger += 1

        if log_func:
            log_func(f"🏙️ **{self.name}**: Реген (+1 HP, +1 SP, +1 Stagger)")

class PassiveHedonism(BasePassive):
    id = "hedonism"
    name = "Гедонизм"
    description = "Не позволяет сбрасывать ваши атаки при разнице скорости 8+. (Но вы все равно деретесь с Помехой)."


# ==========================================
# Тату "Благословение Ветра" (Blessing of Wind)
# ==========================================
class PassiveBlessingOfWind(BasePassive):
    id = "blessing_of_wind"
    name = "Тату 'Благословение Ветра'"
    description = "Пассивно: +1 к Атаке и Уклонению за каждые 5 Дыма. Лимит Дыма увеличен на 5."

    def on_combat_start(self, unit, log_func):
        # Увеличиваем лимит дыма в памяти юнита. SmokeStatus это увидит.
        unit.memory['smoke_limit_bonus'] = 5
        if log_func: log_func(f"🌬️ **{self.name}**: Лимит дыма увеличен до 15")

    def on_roll(self, ctx: RollContext):
        smoke = ctx.source.get_status("smoke")
        # Если дыма меньше 5, бонуса нет
        if smoke < 5: return

        # Бонус: 1 за 5, 2 за 10, 3 за 15, 4 за 20, 5 за 25
        bonus = smoke // 5

        # Работает только на Атакующие кубики и Уклонение
        # (Slash, Pierce, Blunt, Evade)
        if ctx.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT, DiceType.EVADE]:
            ctx.modify_power(bonus, f"Blessing ({smoke})")


# ==========================================
# Живи быстро, умирай молодым (Live Fast, Die Young)
# ==========================================
class PassiveLiveFastDieYoung(BasePassive):
    id = "live_fast_die_young"
    name = "Живи быстро, умирай молодым"
    description = "Каждый кубик скорости даёт +1 к Силе и Стойкости в начале сцены. +1 Дым за победу в столкновении атакой."

    def on_combat_start(self, unit, log_func):
        # ИСПРАВЛЕНИЕ: Считаем реальные активные слоты (unit.active_slots),
        # а не базовые характеристики. Это учитывает Ярость, Ускорение и другие бонусы.
        slots_count = len(unit.active_slots) if unit.active_slots else 1

        # Накладываем баффы
        unit.add_status("strength", slots_count)
        unit.add_status("endurance", slots_count)

        if log_func:
            log_func(f"⚡ **{self.name}**: +{slots_count} Силы и Стойкости (за {slots_count} слота)")

    def on_clash_win(self, ctx: RollContext):
        # Если выиграли атакующим кубиком -> +1 Дым
        if ctx.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            ctx.source.add_status("smoke", 1, duration=99)
            ctx.log.append(f"⚡ **{self.name}**: +1 Дым за победу")