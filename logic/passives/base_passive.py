from logic.context import RollContext

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

