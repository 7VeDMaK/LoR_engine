# logic/clash_flow.py
from core.models import DiceType, Dice
from logic.clash_mechanics import ClashMechanicsMixin


class ClashFlowMixin(ClashMechanicsMixin):
    """
    Уровень 2: Сценарии стычек.
    - Полный цикл Clash
    - Односторонняя атака
    - Таблица взаимодействий кубиков (Interaction Table)
    """

    # --- [NEW] Хелпер для форматирования "Base + Bonus" ---
    def _fmt_roll(self, ctx):
        if not ctx: return "0"
        bonus = ctx.final_value - ctx.base_value
        sign = "+" if bonus >= 0 else ""
        # Пример: 5 + 9
        return f"{ctx.base_value} {sign} {bonus}"

    # -----------------------------------------------------

    def _resolve_card_clash(self, attacker, defender, round_label: str, is_p1_attacker: bool):
        report = []
        ac = attacker.current_card
        dc = defender.current_card

        self._process_card_self_scripts("on_use", attacker, defender)
        self._process_card_self_scripts("on_use", defender, attacker)

        max_dice = max(len(ac.dice_list), len(dc.dice_list))

        for j in range(max_dice):
            # Проверяем стаггер/смерть ПЕРЕД каждым кубиком
            atk_alive = not (attacker.is_dead() or attacker.is_staggered())
            def_alive = not (defender.is_dead() or defender.is_staggered())

            # Если оба выбыли - прерываем
            if not atk_alive and not def_alive: break

            # Берем кубики, если юнит способен действовать
            die_a = ac.dice_list[j] if (j < len(ac.dice_list) and atk_alive) else None
            die_d = dc.dice_list[j] if (j < len(dc.dice_list) and def_alive) else None

            # Если кубики кончились у обоих
            if not die_a and not die_d: break

            ctx_a = self._create_roll_context(attacker, defender, die_a)
            ctx_d = self._create_roll_context(defender, attacker, die_d)

            val_a = ctx_a.final_value if ctx_a else 0
            val_d = ctx_d.final_value if ctx_d else 0

            # --- [UPDATED] Форматируем лог (Base + Mod) ---
            str_a = self._fmt_roll(ctx_a)
            str_d = self._fmt_roll(ctx_d)

            # P1 всегда слева для консистентности
            val_p1_str = str_a if is_p1_attacker else str_d
            val_p2_str = str_d if is_p1_attacker else str_a

            res_str = f"{val_p1_str} vs {val_p2_str}"
            # ----------------------------------------------

            detail = ""

            if ctx_a and ctx_d:
                # --- ПОЛНОЦЕННЫЙ КЛЕШ ---
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
                # --- У ЗАЩИТНИКА НЕТ КУБИКА (ИЛИ ОН СТАГГЕРНУТ) ---
                if ctx_a.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
                    detail = "Unanswered Hit"
                    self._apply_damage(ctx_a, None, "hp")
                else:
                    detail = "Defensive (Skipped)"

            elif ctx_d:
                # --- У АТАКУЮЩЕГО НЕТ КУБИКА ---
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
        """Определяет эффект победы в зависимости от типа кубиков"""
        w_type = winner_ctx.dice.dtype
        l_type = loser_ctx.dice.dtype

        w_is_atk = w_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]
        l_is_atk = l_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]

        w_is_blk = w_type == DiceType.BLOCK
        l_is_blk = l_type == DiceType.BLOCK
        w_is_evd = w_type == DiceType.EVADE
        l_is_evd = l_type == DiceType.EVADE

        # 1. АТАКА ПОБЕДИЛА
        if w_is_atk:
            if l_is_atk:
                # Atk vs Atk: Полный урон по HP
                self._apply_damage(winner_ctx, loser_ctx, "hp")
            elif l_is_blk:
                # Atk vs Block: Урон по HP = (Атака - Блок)
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "hp")
            elif l_is_evd:
                # Atk vs Evade: Полный урон
                self._apply_damage(winner_ctx, loser_ctx, "hp")

        # 2. БЛОК ПОБЕДИЛ
        elif w_is_blk:
            if l_is_atk:
                # Block vs Atk: Парирование -> Stagger урон атакующему
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "stagger")
            elif l_is_blk:
                # Block vs Block: Stagger урон проигравшему
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "stagger")
            elif l_is_evd:
                # Block vs Evade: Stagger урон уклоняющемуся
                damage_amt = diff
                self._deal_direct_damage(winner_ctx, loser_ctx.source, damage_amt, "stagger")

        # 3. УКЛОНЕНИЕ ПОБЕДИЛО
        elif w_is_evd:
            winner_ctx.log.append("💨 Dodged!")

    def _resolve_one_sided(self, source, target, round_label: str):
        report = []
        card = source.current_card
        self._process_card_self_scripts("on_use", source, target)

        # === ЛОГИКА ПАССИВКИ "Махнуть хвостиком" (Wag the Tail) ===
        reaction_die = None

        # Проверяем наличие пассивки у цели
        if "wag_tail" in target.passives:
            # 1. Создаем БАЗОВЫЙ кубик 5-7 (без бонусов)
            min_v = 5
            max_v = 7
            reaction_die = Dice(min_v, max_v, DiceType.EVADE)

            # 2. Логируем активацию
            report.append({
                "round": "Reaction",
                "rolls": "Passive",
                "details": f"🦊 **{target.name}** prepares to Wag the Tail! (Base Evade {min_v}-{max_v})"
            })
        # ==========================================================

        for j, die in enumerate(card.dice_list):
            if source.is_dead() or target.is_dead() or source.is_staggered(): break

            ctx = self._create_roll_context(source, target, die)
            val = ctx.final_value

            # --- [UPDATED] Формат ролла атакующего ---
            roll_display = self._fmt_roll(ctx)
            # -----------------------------------------

            detail = "One-Sided"

            # В односторонней атаке работают только атакующие кубики
            if die.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:

                # --- ОБРАБОТКА РЕАКЦИИ (УКЛОНЕНИЕ) ---
                hit_successful = True

                if reaction_die:
                    # Кидаем кубик реакции (защитника)
                    def_ctx = self._create_roll_context(target, source, reaction_die)

                    # --- [NEW] Применяем бонус пассивки (Level / 10) здесь ---
                    # Чтобы в логе было видно "+X"
                    if "wag_tail" in target.passives:
                        bonus = max(0, target.level // 10)
                        if bonus > 0:
                            def_ctx.modify_power(bonus, "Tail Mastery")

                    val_def = def_ctx.final_value

                    # Обновляем строку роллов: Атака vs Уворот
                    roll_display = f"{self._fmt_roll(ctx)} vs {self._fmt_roll(def_ctx)}"

                    if val_def > val:
                        # УСПЕШНОЕ УКЛОНЕНИЕ
                        detail += " 💨 Dodged! (Tail)"
                        hit_successful = False
                        # Кубик НЕ уничтожается (Recycle), он попробует уклониться от следующего удара
                    else:
                        # ПРОВАЛ
                        detail += " (Fail)"
                        reaction_die = None  # Кубик "ломается" и исчезает

                if hit_successful:
                    self._apply_damage(ctx, None, "hp")
                # -------------------------------------

            else:
                detail = "Defensive Die (Skipped)"

            if ctx.log: detail += " | " + " ".join(ctx.log)
            report.append({"round": f"{round_label} (D{j + 1})", "rolls": roll_display, "details": detail})

        return report