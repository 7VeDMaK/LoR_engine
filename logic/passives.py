from logic.context import RollContext
from core.enums import DiceType
from core.models import Dice


class BasePassive:
    id = "base"
    name = "Base Passive"
    description = "No description"
    is_active_ability = False
    cooldown = 0
    duration = 0

    def on_combat_start(self, unit, log_func): pass

    def on_combat_end(self, unit, log_func): pass

    def on_round_start(self, unit, log_func): pass

    def on_round_end(self, unit, log_func): pass

    def on_roll(self, ctx: RollContext): pass

    def on_clash_win(self, ctx: RollContext): pass

    def on_clash_lose(self, ctx: RollContext): pass

    def on_hit(self, ctx: RollContext): pass

    def activate(self, unit, log_func): pass

    def modify_stats(self, unit, stats: dict, logs: list): pass

    def modify_clash_interaction(self, ctx, interaction, loser_ctx): pass

    def modify_clash_interaction_loser(self, ctx, interaction, winner_ctx): pass

    def get_virtual_defense_die(self, unit, incoming_die): return None


# ==========================================
# Махнуть хвостиком (Wag Tail)
# ==========================================
class PassiveWagTail(BasePassive):
    id = "wag_tail"
    name = "Махнуть хвостиком"
    description = "При односторонней атаке автоматически использует Уклонение (5-7)."

    def get_virtual_defense_die(self, unit, incoming_die):
        # Тут мы не можем писать в лог, так как метод возвращает объект
        # Лог будет в clash_flow, когда сработает "Auto-Def"
        d_min = 5
        d_max = 7
        return Dice(d_min, d_max, DiceType.EVADE)


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
    description = "Медленно восстанавливает ресурсы в конце хода."

    def on_round_end(self, unit, log_func):
        unit.heal_hp(1)
        if unit.current_sp < unit.max_sp: unit.current_sp += 1
        if unit.current_stagger < unit.max_stagger: unit.current_stagger += 1

        if log_func:
            log_func(f"🏙️ **{self.name}**: Отдых в переулке... (+1 HP, +1 SP, +1 Stagger)")


# === РЕГИСТРАЦИЯ ===
PASSIVE_REGISTRY = {
    "wag_tail": PassiveWagTail(),
    "backstreet_demon": PassiveBackstreetDemon(),
    "daughter_of_backstreets": PassiveDaughterOfBackstreets(),
}