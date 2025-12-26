# logic/clash_flow.py
from core.models import DiceType, Dice
from logic.clash_mechanics import ClashMechanicsMixin


class ClashFlowMixin(ClashMechanicsMixin):

    def _fmt_roll(self, ctx):
        """Форматирует вывод: Base + Bonus"""
        if not ctx: return "0"
        bonus = ctx.final_value - ctx.base_value
        sign = "+" if bonus >= 0 else ""
        return f"{ctx.base_value} {sign} {bonus}"

    def _resolve_card_clash(self, attacker, defender, round_label: str, is_p1_attacker: bool):
        report = []
        ac = attacker.current_card
        dc = defender.current_card

        self._process_card_self_scripts("on_use", attacker, defender)
        self._process_card_self_scripts("on_use", defender, attacker)

        max_dice = max(len(ac.dice_list), len(dc.dice_list))

        for j in range(max_dice):
            atk_alive = not (attacker.is_dead() or attacker.is_staggered())
            def_alive = not (defender.is_dead() or defender.is_staggered())
            if not atk_alive and not def_alive: break

            die_a = ac.dice_list[j] if (j < len(ac.dice_list) and atk_alive) else None
            die_d = dc.dice_list[j] if (j < len(dc.dice_list) and def_alive) else None

            if not die_a and not die_d: break

            ctx_a = self._create_roll_context(attacker, defender, die_a)
            ctx_d = self._create_roll_context(defender, attacker, die_d)

            val_a = ctx_a.final_value if ctx_a else 0
            val_d = ctx_d.final_value if ctx_d else 0

            str_a = self._fmt_roll(ctx_a)
            str_d = self._fmt_roll(ctx_d)

            val_p1_str = str_a if is_p1_attacker else str_d
            val_p2_str = str_d if is_p1_attacker else str_a

            res_str = f"{val_p1_str} vs {val_p2_str}"
            detail = ""

            if ctx_a and ctx_d:
                # --- CLASH ---
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
                if ctx_a.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
                    detail = "Unanswered Hit"
                    self._apply_damage(ctx_a, None, "hp")
                else:
                    detail = "Defensive (Skipped)"

            elif ctx_d:
                if ctx_d.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
                    detail = "Unanswered Hit"
                    self._apply_damage(ctx_d, None, "hp")
                else:
                    detail = "Defensive (Skipped)"

            round_logs = []
            if ctx_a: round_logs.extend(ctx_a.log)
            if ctx_d: round_logs.extend(ctx_d.log)
            if round_logs: detail += " | " + " ".join(round_logs)

            report.append({"round": f"{round_label} (D{j + 1})", "rolls": res_str, "details": detail})
        return report

    def _resolve_clash_interaction(self, winner_ctx, loser_ctx, diff: int):
        """Обработка победы в столкновении"""
        w_type = winner_ctx.dice.dtype
        l_type = loser_ctx.dice.dtype

        w_is_atk = w_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]
        l_is_atk = l_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]
        w_is_blk = w_type == DiceType.BLOCK
        l_is_blk = l_type == DiceType.BLOCK
        w_is_evd = w_type == DiceType.EVADE

        if w_is_atk:
            if l_is_atk:
                self._apply_damage(winner_ctx, loser_ctx, "hp")
            elif l_is_blk:
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "hp")
            elif w_is_evd:  # (невозможный кейс для атаки, но оставим структуру)
                pass
            else:  # Atk vs Evade (Loss) -> обрабатывается в блоке победителя (Evade)
                pass

        elif w_is_blk:
            if l_is_atk or l_is_blk:
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "stagger")

        elif w_is_evd:
            winner_ctx.log.append("💨 Dodged!")

            # --- [UPDATED] ДЕМОН ПЕРЕУЛКА (CLASH) ---
            if "alley_demon" in winner_ctx.source.passives:
                # Берем ИТОГОВОЕ значение проигравшего (loser_ctx.final_value)
                attack_val = loser_ctx.final_value
                counter_dmg = attack_val // 2

                if counter_dmg > 0:
                    self._deal_direct_damage(winner_ctx, loser_ctx.source, counter_dmg, "hp")
                    winner_ctx.log.append(f"👿 Counter {counter_dmg} (Half of {attack_val})")
            # ----------------------------------------

    def _resolve_one_sided(self, source, target, round_label: str):
        report = []
        card = source.current_card
        self._process_card_self_scripts("on_use", source, target)

        reaction_die = None
        # Wag the Tail logic
        if "wag_tail" in target.passives:
            min_v = 5
            max_v = 7
            reaction_die = Dice(min_v, max_v, DiceType.EVADE)
            report.append({
                "round": "Reaction",
                "rolls": "Passive",
                "details": f"🦊 **{target.name}** prepares to Wag the Tail! (Base {min_v}-{max_v})"
            })

        for j, die in enumerate(card.dice_list):
            if source.is_dead() or target.is_dead() or source.is_staggered(): break

            ctx = self._create_roll_context(source, target, die)

            # Итоговое значение атаки (с бонусами)
            val = ctx.final_value

            roll_display = self._fmt_roll(ctx)
            detail = "One-Sided"

            if die.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
                hit_successful = True

                if reaction_die:
                    def_ctx = self._create_roll_context(target, source, reaction_die)

                    val_def = def_ctx.final_value
                    roll_display = f"{self._fmt_roll(ctx)} vs {self._fmt_roll(def_ctx)}"

                    if val_def > val:
                        detail += " 💨 Dodged! (Tail)"
                        hit_successful = False

                        # --- [UPDATED] ДЕМОН ПЕРЕУЛКА (ONE-SIDED) ---
                        if "alley_demon" in target.passives:
                            # Урон = половина от ИТОГОВОГО значения атаки (val)
                            counter_dmg = val // 2
                            if counter_dmg > 0:
                                self._deal_direct_damage(def_ctx, source, counter_dmg, "hp")
                                detail += f" | 👿 Counter {counter_dmg}"
                        # --------------------------------------------
                    else:
                        detail += " (Fail)"
                        reaction_die = None

                if hit_successful:
                    self._apply_damage(ctx, None, "hp")
            else:
                detail = "Defensive Die (Skipped)"

            if ctx.log: detail += " | " + " ".join(ctx.log)
            report.append({"round": f"{round_label} (D{j + 1})", "rolls": roll_display, "details": detail})

        return report