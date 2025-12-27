# logic/clash_flow.py
from core.models import DiceType
from logic.clash_mechanics import ClashMechanicsMixin


class ClashFlowMixin(ClashMechanicsMixin):
    """
    Уровень 2: Сценарии стычек.
    Формирует структуру лога для UI: Left (P1) vs Right (P2).
    """

    # logic/clash_flow.py (Начало метода _resolve_card_clash)

    def _resolve_card_clash(self, attacker, defender, round_label: str, is_p1_attacker: bool, slot_a=None, slot_d=None):
        report = []
        ac = attacker.current_card
        dc = defender.current_card

        # 1. Собираем логи эффектов "При использовании" (On Use)
        on_use_logs = []
        self._process_card_self_scripts("on_use", attacker, defender, custom_log_list=on_use_logs)
        self._process_card_self_scripts("on_use", defender, attacker, custom_log_list=on_use_logs)

        max_dice = max(len(ac.dice_list), len(dc.dice_list))

        for j in range(max_dice):
            # ... (дальше идет стандартная проверка на смерть/стаггер, как было) ...
            atk_alive = not (attacker.is_dead() or attacker.is_staggered())
            def_alive = not (defender.is_dead() or defender.is_staggered())

            if not atk_alive and not def_alive: break

            die_a = ac.dice_list[j] if (j < len(ac.dice_list) and atk_alive) else None
            die_d = dc.dice_list[j] if (j < len(dc.dice_list) and def_alive) else None

            if not die_a and not die_d: break

            # ... (создание контекстов ctx_a, ctx_d) ...
            ctx_a = self._create_roll_context(attacker, defender, die_a)
            ctx_d = self._create_roll_context(defender, attacker, die_d)

            val_a = ctx_a.final_value if ctx_a else 0
            val_d = ctx_d.final_value if ctx_d else 0

            # ... (сбор left_info и right_info остается без изменений) ...
            left_info = {
                "unit": attacker.name if is_p1_attacker else defender.name,
                "card": ac.name if is_p1_attacker else dc.name,
                "dice": (die_a.dtype.name if die_a else "None") if is_p1_attacker else (
                    die_d.dtype.name if die_d else "None"),
                "val": val_a if is_p1_attacker else val_d
            }
            right_info = {
                "unit": defender.name if is_p1_attacker else attacker.name,
                "card": dc.name if is_p1_attacker else ac.name,
                "dice": (die_d.dtype.name if die_d else "None") if is_p1_attacker else (
                    die_a.dtype.name if die_a else "None"),
                "val": val_d if is_p1_attacker else val_a
            }

            outcome = ""
            detail_logs = []

            # === ГЛАВНОЕ ИЗМЕНЕНИЕ ===
            # Если это первый кубик (j=0), добавляем в его описание логи от "On Use"
            if j == 0 and on_use_logs:
                detail_logs.extend(on_use_logs)
            # =========================

            # ... (далее логика победы/поражения, как было) ...
            if ctx_a and ctx_d:
                if val_a > val_d:
                    outcome = f"🏆 {attacker.name} Win"
                    self._handle_clash_win(ctx_a)
                    self._handle_clash_lose(ctx_d)
                    self._resolve_clash_interaction(ctx_a, ctx_d, val_a - val_d)
                # ... (и так далее для остальных условий) ...
                elif val_d > val_a:
                    outcome = f"🏆 {defender.name} Win"
                    self._handle_clash_win(ctx_d)
                    self._handle_clash_lose(ctx_a)
                    self._resolve_clash_interaction(ctx_d, ctx_a, val_d - val_a)
                else:
                    outcome = "🤝 Draw"

            elif ctx_a:
                outcome = f"🏹 {attacker.name} Unanswered"
                if ctx_a.dice.dtype.name in ["SLASH", "PIERCE", "BLUNT"]:
                    self._apply_damage(ctx_a, None, "hp")
                else:
                    outcome += " (Def)"

            elif ctx_d:
                outcome = f"🏹 {defender.name} Unanswered"
                if ctx_d.dice.dtype.name in ["SLASH", "PIERCE", "BLUNT"]:
                    self._apply_damage(ctx_d, None, "hp")
                else:
                    outcome += " (Def)"

            # Сбор логов от самих кубиков
            if ctx_a: detail_logs.extend(ctx_a.log)
            if ctx_d: detail_logs.extend(ctx_d.log)

            report.append({
                "type": "clash",
                "round": f"{round_label} (D{j + 1})",
                "left": left_info,
                "right": right_info,
                "outcome": outcome,
                "details": detail_logs
            })

        return report

    def _resolve_clash_interaction(self, winner_ctx, loser_ctx, diff: int):
        """Определяет эффект победы в зависимости от типа кубиков"""
        w_type = winner_ctx.dice.dtype
        l_type = loser_ctx.dice.dtype

        # Определение типа (Atk, Block, Evade)
        w_is_atk = w_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]
        l_is_atk = l_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]
        w_is_blk = w_type == DiceType.BLOCK
        l_is_blk = l_type == DiceType.BLOCK
        w_is_evd = w_type == DiceType.EVADE
        l_is_evd = l_type == DiceType.EVADE

        if w_is_atk:
            if l_is_atk:
                self._apply_damage(winner_ctx, loser_ctx, "hp")
            elif l_is_blk:
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "hp")
            elif l_is_evd:
                self._apply_damage(winner_ctx, loser_ctx, "hp")

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

        elif w_is_evd:
            winner_ctx.log.append("💨 Dodged!")

    def _resolve_one_sided(self, source, target, round_label: str):
        report = []
        card = source.current_card

        # 1. Ловим логи
        on_use_logs = []
        self._process_card_self_scripts("on_use", source, target, custom_log_list=on_use_logs)

        for j, die in enumerate(card.dice_list):
            if source.is_dead() or target.is_dead() or source.is_staggered(): break

            ctx = self._create_roll_context(source, target, die)

            left_info = {
                "unit": source.name, "card": card.name,
                "dice": die.dtype.name, "val": ctx.final_value
            }
            right_info = {
                "unit": target.name, "card": "---", "dice": "None", "val": 0
            }

            detail = "Unopposed"
            if die.dtype.name in ["SLASH", "PIERCE", "BLUNT"]:
                self._apply_damage(ctx, None, "hp")
            else:
                detail = "Defensive (Skipped)"

            # Собираем все логи
            all_logs = []
            # Если первый дайс - добавляем On Use
            if j == 0 and on_use_logs:
                all_logs.extend(on_use_logs)
            all_logs.extend(ctx.log)

            report.append({
                "type": "onesided",
                "round": f"{round_label} (D{j + 1})",
                "left": left_info, "right": right_info,
                "outcome": detail, "details": all_logs
            })

        return report