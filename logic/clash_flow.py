from core.models import DiceType
from logic.clash_mechanics import ClashMechanicsMixin


class ClashFlowMixin(ClashMechanicsMixin):
    """
    Логика разрешения конкретных стычек (Flow):
    - _resolve_card_clash (Полный цикл столкновения двух карт)
    - _resolve_clash_interaction (Кто кого перебил и какой эффект)
    - _resolve_one_sided (Односторонняя атака)
    """

    def _resolve_card_clash(self, attacker, defender, round_label: str, is_p1_attacker: bool):
        report = []
        ac = attacker.current_card
        dc = defender.current_card

        self._process_card_self_scripts("on_use", attacker, defender)
        self._process_card_self_scripts("on_use", defender, attacker)

        max_dice = max(len(ac.dice_list), len(dc.dice_list))

        for j in range(max_dice):
            if attacker.is_dead() or defender.is_dead() or attacker.is_staggered(): break

            die_a = ac.dice_list[j] if j < len(ac.dice_list) else None
            die_d = dc.dice_list[j] if j < len(dc.dice_list) else None

            ctx_a = self._create_roll_context(attacker, defender, die_a)
            ctx_d = self._create_roll_context(defender, attacker, die_d)

            val_a = ctx_a.final_value if ctx_a else 0
            val_d = ctx_d.final_value if ctx_d else 0

            # Форматируем лог
            val_p1 = val_a if is_p1_attacker else val_d
            val_p2 = val_d if is_p1_attacker else val_a
            res_str = f"{val_p1} vs {val_p2}"

            detail = ""

            if ctx_a and ctx_d:
                if val_a > val_d:
                    detail = f"{attacker.name} Win!"
                    self._handle_clash_win(ctx_a)
                    self._handle_clash_lose(ctx_d)

                    self._resolve_clash_interaction(ctx_a, ctx_d, val_a - val_d)

                elif val_d > val_a:
                    detail = f"{defender.name} Win!"
                    self._handle_clash_win(ctx_d)
                    self._handle_clash_lose(ctx_a)

                    self._resolve_clash_interaction(ctx_d, ctx_a, val_d - val_a)

                else:
                    detail = "Draw!"
            elif ctx_a:
                detail = "Unanswered"
                self._apply_damage(ctx_a, None, "hp")
            elif ctx_d:
                detail = "Unanswered"
                self._apply_damage(ctx_d, None, "hp")

            round_logs = []
            if ctx_a: round_logs.extend(ctx_a.log)
            if ctx_d: round_logs.extend(ctx_d.log)
            if round_logs: detail += " | " + " ".join(round_logs)

            report.append({"round": f"{round_label} (D{j + 1})", "rolls": res_str, "details": detail})
        return report

    def _resolve_clash_interaction(self, winner_ctx, loser_ctx, diff: int):
        w_type = winner_ctx.dice.dtype
        l_type = loser_ctx.dice.dtype

        w_is_atk = w_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]
        l_is_atk = l_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]

        w_is_blk = w_type == DiceType.BLOCK
        l_is_blk = l_type == DiceType.BLOCK
        w_is_evd = w_type == DiceType.EVADE
        l_is_evd = l_type == DiceType.EVADE

        # 1. ATTACK WINS
        if w_is_atk:
            if l_is_atk:
                self._apply_damage(winner_ctx, loser_ctx, "hp")
            elif l_is_blk:
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "hp")
            elif l_is_evd:
                self._apply_damage(winner_ctx, loser_ctx, "hp")

        # 2. BLOCK WINS
        elif w_is_blk:
            if l_is_atk:
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "stagger")
            elif l_is_blk:
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "stagger")
            elif l_is_evd:
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "stagger")

        # 3. EVADE WINS
        elif w_is_evd:
            winner_ctx.log.append("💨 Dodged!")

    def _resolve_one_sided(self, source, target, round_label: str):
        report = []
        card = source.current_card
        self._process_card_self_scripts("on_use", source, target)

        for j, die in enumerate(card.dice_list):
            if source.is_dead() or target.is_dead() or source.is_staggered(): break

            ctx = self._create_roll_context(source, target, die)
            val = ctx.final_value

            detail = "One-Sided"

            if die.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
                self._apply_damage(ctx, None, "hp")
            else:
                detail = "Defensive Die (Skipped)"

            if ctx.log: detail += " | " + " ".join(ctx.log)
            report.append({"round": f"{round_label} (D{j + 1})", "rolls": f"{val}", "details": detail})

        return report