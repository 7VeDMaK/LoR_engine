# logic/passives.py
from logic.context import RollContext
from core.enums import DiceType
from core import dice

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

# --- НОВЫЕ ПАССИВКИ ---

class PassiveTailSwipe(BasePassive):
    id = "wag_tail"
    name = "Махнуть хвостиком"
    description = "При односторонней атаке по вам: создается защитный кубик уклонения (5-7). Кубик сохраняется при победе."

class PassiveAlleyDemon(BasePassive):
    id = "alley_demon"
    name = "Демон переулка"
    description = "После успешного уворота наносит атакующему урон (HP), равный половине итогового значения атаки противника."


class PassiveDaughterOfBackstreets(BasePassive):
    id = "daughter_of_backstreets"
    name = "Дочь переулка"
    description = "Медленно восстанавливает 1 HP, 1 SP и 1 Stagger в конце каждого хода."

    def on_round_end(self, unit, log_func):
        # 1. Восстанавливаем HP (используем встроенный метод для учета бонусов лечения)
        unit.heal_hp(1)

        # 2. Восстанавливаем SP
        if unit.current_sp < unit.max_sp:
            unit.current_sp += 1

        # 3. Восстанавливаем Stagger
        if unit.current_stagger < unit.max_stagger:
            unit.current_stagger += 1

        # Лог для отчета
        if log_func:
            log_func(f"🏙️ {self.name}: Восстановлено 1 HP, 1 SP, 1 Stagger")

# --- РЕЕСТР ---
PASSIVE_REGISTRY = {
    "wag_tail": PassiveTailSwipe(),
    "alley_demon": PassiveAlleyDemon(),
    "daughter_of_backstreets": PassiveDaughterOfBackstreets(),
}