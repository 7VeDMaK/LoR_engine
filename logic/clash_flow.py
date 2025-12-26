from core.enums import DiceType
from logic.clash_mechanics import ClashMechanicsMixin
from logic.passives import PASSIVE_REGISTRY
from logic.talents import TALENT_REGISTRY


class ClashFlowMixin(ClashMechanicsMixin):
    """
    Уровень 2: Сценарии стычек.
    Обеспечивает поток хода и красивые логи.
    """

    def _resolve_card_clash(self, attacker, defender, round_label: str, is_p1_attacker: bool):
        report = []
        ac = attacker.current_card
        dc = defender.current_card

        self._process_card_self_scripts("on_use", attacker, defender)
        self._process_card_self_scripts("on_use", defender, attacker)

        max_dice = max(len(ac.dice_list), len(dc.dice_list))

        for j in range(max_dice):
            if attacker.is_dead() or attacker.is_staggered(): break
            if defender.is_dead() or defender.is_staggered(): break

            die_a = ac.dice_list[j] if j < len(ac.dice_list) else None
            die_d = dc.dice_list[j] if j < len(dc.dice_list) else None

            if not die_a and not die_d: break

            ctx_a = self._create_roll_context(attacker, defender, die_a)
            ctx_d = self._create_roll_context(defender, attacker, die_d)

            val_a = ctx_a.final_value if ctx_a else 0
            val_d = ctx_d.final_value if ctx_d else 0

            val_p1 = val_a if is_p1_attacker else val_d
            val_p2 = val_d if is_p1_attacker else val_a
            res_str = f"{val_p1} vs {val_p2}"
            detail = ""

            if ctx_a and ctx_d:
                # === CLASH ===
                diff = abs(val_a - val_d)

                if val_a > val_d:
                    detail = f"{attacker.name} Win!"
                    self._handle_clash_win(ctx_a)
                    self._handle_clash_lose(ctx_d)
                    self._execute_clash_interaction(ctx_a, ctx_d, diff)
                elif val_d > val_a:
                    detail = f"{defender.name} Win!"
                    self._handle_clash_win(ctx_d)
                    self._handle_clash_lose(ctx_a)
                    self._execute_clash_interaction(ctx_d, ctx_a, diff)
                else:
                    detail = "Draw!"

            elif ctx_a:
                # Односторонняя атака Атакующего
                detail = self._resolve_unopposed(ctx_a, defender)

            elif ctx_d:
                # Односторонняя атака Защитника
                detail = self._resolve_unopposed(ctx_d, attacker)

            # === СБОРКА ЛОГОВ С ИМЕНАМИ ===
            round_logs = []
            if ctx_a:
                # Добавляем имя к каждой строке лога
                round_logs.extend([f"⚔️ {attacker.name}: {l}" for l in ctx_a.log])

            if ctx_d:
                round_logs.extend([f"🛡️ {defender.name}: {l}" for l in ctx_d.log])

            if round_logs:
                # Красивый перенос строк
                formatted_logs = "\n".join([f"• {l}" for l in round_logs])
                detail += "\n" + formatted_logs

            report.append({"round": f"{round_label} (D{j + 1})", "rolls": res_str, "details": detail})

        return report

    def _resolve_one_sided(self, source, target, round_label: str):
        """Полный цикл односторонней атаки."""
        report = []
        card = source.current_card
        self._process_card_self_scripts("on_use", source, target)

        for j, die in enumerate(card.dice_list):
            if source.is_dead() or target.is_dead() or source.is_staggered(): break

            ctx = self._create_roll_context(source, target, die)
            val = ctx.final_value

            # Вся логика защиты (включая логи) вернется из _resolve_unopposed
            detail = self._resolve_unopposed(ctx, target)

            # Добавляем логи атакующего (если они еще не добавлены)
            if ctx.log:
                # Явно пишем, что это логи атакующего
                atk_logs = "\n".join([f"• ⚔️ {source.name}: {l}" for l in ctx.log])
                detail += "\n" + atk_logs

            report.append({"round": f"{round_label} (D{j + 1})", "rolls": f"{val}", "details": detail})

        return report

    def _resolve_unopposed(self, source_ctx, target):
        """
        Обработка безответного удара.
        Ищет пассивки защиты (get_virtual_defense_die) и показывает их логи.
        """
        # 1. Поиск виртуальной защиты
        virtual_die = None
        for pid in target.passives + target.talents:
            obj = PASSIVE_REGISTRY.get(pid) or TALENT_REGISTRY.get(pid)
            if obj and hasattr(obj, "get_virtual_defense_die"):
                virtual_die = obj.get_virtual_defense_die(target, source_ctx.dice)
                if virtual_die: break

        # 2. Если защита есть
        if virtual_die:
            # Создаем контекст броска для защиты. ТЕПЕРЬ ОН СОЗДАЕТ ЛОГИ ВНУТРИ def_ctx!
            def_ctx = self._create_roll_context(target, source_ctx.source, virtual_die)
            val_atk = source_ctx.final_value
            val_def = def_ctx.final_value

            res_str = f"🛡️Auto-Def {val_def} vs ⚔️{val_atk}"

            # Извлекаем логи защитника, чтобы показать их игроку
            def_logs_list = [f"• 🛡️ {target.name} (Auto): {l}" for l in def_ctx.log]
            def_logs_str = "\n".join(def_logs_list)

            result_str = ""

            if val_def > val_atk:
                # ПОБЕДА ЗАЩИТЫ
                self._handle_clash_win(def_ctx)
                self._handle_clash_lose(source_ctx)
                diff = max(0, val_def - val_atk)
                self._execute_clash_interaction(def_ctx, source_ctx, diff)
                result_str = f"{res_str} | **Defended!**"

            elif val_atk > val_def:
                # ПРОБИТИЕ ЗАЩИТЫ
                self._handle_clash_win(source_ctx)
                self._handle_clash_lose(def_ctx)
                diff = max(0, val_atk - val_def)
                self._execute_clash_interaction(source_ctx, def_ctx, diff)
                result_str = f"{res_str} | **Defense Broken!**"
            else:
                result_str = f"{res_str} | Draw"

            # Возвращаем строку результата + логи защиты
            return f"{result_str}\n{def_logs_str}"

        # 3. Если защиты нет
        if source_ctx.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            self._apply_damage(source_ctx, None, "hp")
            return "Unanswered Hit"
        else:
            return "Defensive Die (Skipped)"

    def _execute_clash_interaction(self, winner_ctx, loser_ctx, diff: int):
        # 1. Стандарт
        interaction = self._calculate_standard_interaction(winner_ctx, loser_ctx, diff)

        # 2. Хуки (победитель и проигравший)
        self._dispatch_event("modify_clash_interaction", winner_ctx, interaction, loser_ctx)
        self._dispatch_event("modify_clash_interaction_loser", loser_ctx, interaction, winner_ctx)

        # 3. Применение
        if interaction["action"] == "damage":
            target = interaction["target"]
            if interaction.get("is_full_attack", False):
                self._apply_damage(winner_ctx, loser_ctx, interaction["dmg_type"])
            else:
                self._deal_direct_damage(winner_ctx, target, interaction["amount"], interaction["dmg_type"])

        elif interaction["action"] == "evade_success":
            winner_ctx.log.append("💨 Dodged!")

    def _calculate_standard_interaction(self, winner_ctx, loser_ctx, diff: int) -> dict:
        w_type = winner_ctx.dice.dtype
        l_type = loser_ctx.dice.dtype

        # ... (стандартная логика типов кубиков, без изменений) ...
        # Для краткости: Атака бьет Атаку, Блок бьет Атаку в стаггер, и т.д.

        w_is_atk = w_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]
        l_is_atk = l_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]
        w_is_blk = w_type == DiceType.BLOCK
        w_is_evd = w_type == DiceType.EVADE

        result = {
            "action": "nothing",
            "dmg_type": "hp",
            "amount": 0,
            "target": loser_ctx.source,
            "is_full_attack": False
        }

        if w_is_atk:
            if l_is_atk:
                result.update({"action": "damage", "dmg_type": "hp", "is_full_attack": True})
            elif l_type == DiceType.BLOCK:
                result.update({"action": "damage", "dmg_type": "hp", "amount": diff})
            else:
                result.update({"action": "damage", "dmg_type": "hp", "is_full_attack": True})
        elif w_is_blk:
            result.update({"action": "damage", "dmg_type": "stagger", "amount": diff})
        elif w_is_evd:
            result.update({"action": "evade_success"})

        return result