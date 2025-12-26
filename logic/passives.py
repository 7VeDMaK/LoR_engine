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

# --- РЕЕСТР ---
PASSIVE_REGISTRY = {
    "wag_tail": PassiveTailSwipe(),
    "alley_demon": PassiveAlleyDemon()
}