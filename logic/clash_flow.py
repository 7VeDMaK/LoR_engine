# logic/clash_flow.py
from core.models import DiceType
from logic.clash_mechanics import ClashMechanicsMixin


class ClashFlowMixin(ClashMechanicsMixin):

    def _resolve_card_clash(self, attacker, defender, round_label: str, is_p1_attacker: bool, slot_a=None, slot_d=None):
        report = []
        ac = attacker.current_card
        dc = defender.current_card

        on_use_logs = []
        self._process_card_self_scripts("on_use", attacker, defender, custom_log_list=on_use_logs)
        self._process_card_self_scripts("on_use", defender, attacker, custom_log_list=on_use_logs)

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

            # === ОБНОВЛЕННАЯ СТРУКТУРА С ДИАПАЗОНАМИ ===
            left_info = {
                "unit": attacker.name if is_p1_attacker else defender.name,
                "card": ac.name if is_p1_attacker else dc.name,
                "dice": (die_a.dtype.name if die_a else "None") if is_p1_attacker else (
                    die_d.dtype.name if die_d else "None"),
                "val": val_a if is_p1_attacker else val_d,
                # Добавляем диапазон:
                "range": (f"{die_a.min_val}-{die_a.max_val}" if die_a else "-") if is_p1_attacker else (
                    f"{die_d.min_val}-{die_d.max_val}" if die_d else "-")
            }

            right_info = {
                "unit": defender.name if is_p1_attacker else attacker.name,
                "card": dc.name if is_p1_attacker else ac.name,
                "dice": (die_d.dtype.name if die_d else "None") if is_p1_attacker else (
                    die_a.dtype.name if die_a else "None"),
                "val": val_d if is_p1_attacker else val_a,
                # Добавляем диапазон:
                "range": (f"{die_d.min_val}-{die_d.max_val}" if die_d else "-") if is_p1_attacker else (
                    f"{die_a.min_val}-{die_a.max_val}" if die_a else "-")
            }
            # ==========================================

            outcome = ""
            detail_logs = []

            if j == 0 and on_use_logs:
                detail_logs.extend(on_use_logs)

            if ctx_a and ctx_d:
                if val_a > val_d:
                    outcome = f"🏆 {attacker.name} Win"
                    self._handle_clash_win(ctx_a)
                    self._handle_clash_lose(ctx_d)
                    self._resolve_clash_interaction(ctx_a, ctx_d, val_a - val_d)
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

        # Обработка On Use атакующего
        on_use_logs = []
        self._process_card_self_scripts("on_use", source, target, custom_log_list=on_use_logs)

        for j, die in enumerate(card.dice_list):
            if source.is_dead() or target.is_dead() or source.is_staggered(): break

            # === 1. ПРОВЕРКА НА КОНТР-КУБИК (COUNTER DIE) ===
            # Если цель не в стаггере, ищем у неё активный контр-кубик
            counter_slot_idx, counter_die = self._find_counter_die(target)

            if counter_die and not target.is_staggered():
                # --- ЗАПУСК КОНТР-КЛЕША ---

                # Создаем контексты
                ctx_atk = self._create_roll_context(source, target, die)
                ctx_cnt = self._create_roll_context(target, source, counter_die)

                val_atk = ctx_atk.final_value
                val_cnt = ctx_cnt.final_value

                # UI Данные для отчета
                left_info = {
                    "unit": source.name, "card": card.name,
                    "dice": die.dtype.name, "val": val_atk,
                    "range": f"{die.min_val}-{die.max_val}"
                }
                # Правая сторона - это Контр-кубик
                right_info = {
                    "unit": target.name, "card": "Counter Die",
                    "dice": counter_die.dtype.name, "val": val_cnt,
                    "range": f"{counter_die.min_val}-{counter_die.max_val}"
                }

                outcome = ""
                detail_logs = []
                if j == 0 and on_use_logs: detail_logs.extend(on_use_logs)

                # --- ЛОГИКА ПОБЕДЫ ---
                if val_cnt > val_atk:
                    # COUNTER WIN
                    outcome = f"⚡ Counter Win! ({target.name})"

                    # 1. Атакующий проигрывает (получает урон или стаггер)
                    self._handle_clash_win(ctx_cnt)
                    self._handle_clash_lose(ctx_atk)
                    self._resolve_clash_interaction(ctx_cnt, ctx_atk, val_cnt - val_atk)

                    # 2. ВАЖНО: RECYCLE! Контр-кубик НЕ уничтожается.
                    # Мы просто не помечаем слот как использованный.
                    detail_logs.append("⚡ Counter Die Recycled!")

                elif val_atk > val_cnt:
                    # COUNTER LOSE
                    outcome = f"🗡️ Atk Win! ({source.name})"

                    # 1. Защитник проигрывает (атака проходит)
                    self._handle_clash_win(ctx_atk)
                    self._handle_clash_lose(ctx_cnt)
                    self._resolve_clash_interaction(ctx_atk, ctx_cnt, val_atk - val_cnt)

                    # 2. Контр-кубик ЛОМАЕТСЯ (удаляем его из слота или помечаем слот использованным)
                    self._consume_counter_die(target, counter_slot_idx)
                    detail_logs.append("💔 Counter Die Broken!")

                else:
                    # DRAW
                    outcome = "🤝 Draw"
                    # При ничьей обычно оба удара нивелируются, а контр-кубик тратится
                    self._consume_counter_die(target, counter_slot_idx)
                    detail_logs.append("Counter Die Used (Draw)")

                # Сбор логов
                if ctx_atk: detail_logs.extend(ctx_atk.log)
                if ctx_cnt: detail_logs.extend(ctx_cnt.log)

                report.append({
                    "type": "clash",  # Показываем как Clash
                    "round": f"{round_label} (Counter)",
                    "left": left_info, "right": right_info,
                    "outcome": outcome, "details": detail_logs
                })

                # Если атака была отбита (Counter Win или Draw), переходим к след. кубику атакующего
                # Если атака победила, урон уже нанесен в _resolve_clash_interaction
                continue

                # === 2. ОБЫЧНАЯ ОДНОСТОРОННЯЯ АТАКА (Если нет контры) ===
            ctx = self._create_roll_context(source, target, die)

            left_info = {
                "unit": source.name, "card": card.name,
                "dice": die.dtype.name, "val": ctx.final_value,
                "range": f"{die.min_val}-{die.max_val}"
            }
            right_info = {
                "unit": target.name, "card": "---", "dice": "None", "val": 0, "range": "-"
            }

            detail = "Unopposed"
            if die.dtype.name in ["SLASH", "PIERCE", "BLUNT"]:
                self._apply_damage(ctx, None, "hp")
            else:
                detail = "Defensive (Skipped)"

            all_logs = []
            if j == 0 and on_use_logs: all_logs.extend(on_use_logs)
            all_logs.extend(ctx.log)

            report.append({
                "type": "onesided",
                "round": f"{round_label} (D{j + 1})",
                "left": left_info, "right": right_info,
                "outcome": detail, "details": all_logs
            })

        return report

    def _find_counter_die(self, unit):
        """Ищет первый доступный слот с картой, содержащей is_counter=True."""
        for i, slot in enumerate(unit.active_slots):
            # Проверяем, что слот еще не использован (не executed)
            # Примечание: executed сеты хранятся в ClashSystem, а не здесь.
            # Нам нужно проверить флаг 'consumed' внутри слота, который мы будем ставить.
            if slot.get('consumed', False): continue

            card = slot.get('card')
            if card and card.dice_list:
                first_die = card.dice_list[0]  # Берем первый кубик (у нас Frenzy карты по 1 кубику)
                if getattr(first_die, 'is_counter', False):
                    return i, first_die
        return -1, None

    def _consume_counter_die(self, unit, slot_idx):
        """Помечает слот контр-кубика как использованный (уничтоженный)."""
        if 0 <= slot_idx < len(unit.active_slots):
            unit.active_slots[slot_idx]['consumed'] = True