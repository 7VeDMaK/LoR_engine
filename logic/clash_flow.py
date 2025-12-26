from core.enums import DiceType
from logic.clash_mechanics import ClashMechanicsMixin
from logic.passives import PASSIVE_REGISTRY
from logic.talents import TALENT_REGISTRY


class ClashFlowMixin(ClashMechanicsMixin):
    """
    Уровень 2: Сценарии стычек (Speed Diff, Discard, Clash Loop).
    """

    def _resolve_card_clash(self, attacker, defender, round_label: str, is_p1_attacker: bool, slot_a: dict,
                            slot_d: dict):
        report = []
        ac = attacker.current_card
        dc = defender.current_card

        spd_a = slot_a['speed']
        spd_d = slot_d['speed']

        force_a = slot_a.get('force_clash', False)
        force_d = slot_d.get('force_clash', False)

        self._process_card_self_scripts("on_use", attacker, defender)
        self._process_card_self_scripts("on_use", defender, attacker)

        max_dice = max(len(ac.dice_list), len(dc.dice_list))

        for j in range(max_dice):
            # === 1. ПРОВЕРКА СОСТОЯНИЯ ===
            # Если кто-то умер — бой заканчивается сразу
            if attacker.is_dead() or defender.is_dead(): break

            # Проверяем возможность действовать (Stagger)
            # Если юнит в стаггере, он жив, но не может выставить кубик
            can_act_a = not attacker.is_staggered()
            can_act_d = not defender.is_staggered()

            # Если ОБА в стаггере — бой прерывается (никто ничего не делает)
            if not can_act_a and not can_act_d: break

            # === 2. ПОЛУЧЕНИЕ КУБИКОВ ===
            # Кубик берется только если юнит может действовать
            die_a = ac.dice_list[j] if (j < len(ac.dice_list) and can_act_a) else None
            die_d = dc.dice_list[j] if (j < len(dc.dice_list) and can_act_d) else None

            # Если кубики кончились у обоих (например, у одного 2 куба, у другого 3, и 3-й ход)
            if not die_a and not die_d: break

            # === 3. ЛОГИКА СКОРОСТИ (Только если есть оба кубика) ===
            dis_a = False
            dis_d = False

            # Логика сброса и помехи работает только в КЛЭШЕ (когда оба могут бить)
            if die_a and die_d:
                # 1. Сброс атаки (Атакующий быстрее на 8+)
                if spd_a >= spd_d + 8:
                    must_clash = ("hedonism" in attacker.passives) or force_a
                    if not must_clash:
                        ctx_a = self._create_roll_context(attacker, defender, die_a)
                        detail = f"🚫 **Сброс Атаки!** (Spd {spd_a} vs {spd_d})\n"
                        detail += self._resolve_unopposed(ctx_a, defender)
                        if ctx_a.log:
                            detail += "\n" + "\n".join([f"• ⚔️ {attacker.name}: {l}" for l in ctx_a.log])
                        report.append({"round": f"{round_label} (D{j + 1})", "rolls": f"{ctx_a.final_value} vs ❌",
                                       "details": detail})
                        continue

                # 2. Сброс атаки (Защитник быстрее на 8+)
                if spd_d >= spd_a + 8:
                    must_clash = ("hedonism" in defender.passives) or force_d
                    if not must_clash:
                        ctx_d = self._create_roll_context(defender, attacker, die_d)
                        detail = f"🚫 **Сброс Атаки!** (Spd {spd_d} vs {spd_a})\n"
                        detail += self._resolve_unopposed(ctx_d, attacker)
                        if ctx_d.log:
                            detail += "\n" + "\n".join([f"• 🛡️ {defender.name}: {l}" for l in ctx_d.log])
                        report.append({"round": f"{round_label} (D{j + 1})", "rolls": f"❌ vs {ctx_d.final_value}",
                                       "details": detail})
                        continue

                # 3. Помеха (Разница 4+)
                if spd_a >= spd_d + 4:
                    dis_d = True
                elif spd_d >= spd_a + 4:
                    dis_a = True

            # === 4. БРОСКИ ===
            # Если кубика нет (die_a is None), контекст тоже будет None
            ctx_a = self._create_roll_context(attacker, defender, die_a, is_disadvantage=dis_a)
            ctx_d = self._create_roll_context(defender, attacker, die_d, is_disadvantage=dis_d)

            # Логи Гедонизма
            if die_a and die_d:
                if (spd_a >= spd_d + 8) and (("hedonism" in attacker.passives) or force_a):
                    ctx_a.log.append("🔒 Гедонизм/Lock: Сброс отменен!")
                if (spd_d >= spd_a + 8) and (("hedonism" in defender.passives) or force_d):
                    ctx_d.log.append("🔒 Гедонизм/Lock: Сброс отменен!")

            val_a = ctx_a.final_value if ctx_a else 0
            val_d = ctx_d.final_value if ctx_d else 0
            res_str = f"{val_a if is_p1_attacker else val_d} vs {val_d if is_p1_attacker else val_a}"
            detail = ""

            # === 5. РЕЗОЛВ ===
            if ctx_a and ctx_d:
                # CLASH
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
                # Атакующий бьет (у защитника нет кубика или он в стаггере)
                detail = self._resolve_unopposed(ctx_a, defender)
            elif ctx_d:
                # Защитник бьет (у атакующего нет кубика или он в стаггере)
                detail = self._resolve_unopposed(ctx_d, attacker)

            # Форматирование логов
            round_logs = []
            if ctx_a: round_logs.extend([f"⚔️ {attacker.name}: {l}" for l in ctx_a.log])
            if ctx_d: round_logs.extend([f"🛡️ {defender.name}: {l}" for l in ctx_d.log])
            if round_logs: detail += "\n" + "\n".join([f"• {l}" for l in round_logs])

            report.append({"round": f"{round_label} (D{j + 1})", "rolls": res_str, "details": detail})

        return report

    def _resolve_one_sided(self, source, target, round_label: str):
        report = []
        card = source.current_card
        self._process_card_self_scripts("on_use", source, target)

        for j, die in enumerate(card.dice_list):
            # Прерываем, только если АТАКУЮЩИЙ не может действовать или ЦЕЛЬ мертва.
            # Если ЦЕЛЬ в стаггере - мы ПРОДОЛЖАЕМ бить!
            if source.is_dead() or source.is_staggered(): break
            if target.is_dead(): break

            ctx = self._create_roll_context(source, target, die)
            val = ctx.final_value
            detail = self._resolve_unopposed(ctx, target)
            if ctx.log: detail += "\n" + "\n".join([f"• ⚔️ {source.name}: {l}" for l in ctx.log])
            report.append({"round": f"{round_label} (D{j + 1})", "rolls": f"{val}", "details": detail})
        return report

    def _resolve_unopposed(self, source_ctx, target):
        virtual_die = None
        for pid in target.passives + target.talents:
            obj = PASSIVE_REGISTRY.get(pid) or TALENT_REGISTRY.get(pid)
            if obj and hasattr(obj, "get_virtual_defense_die"):
                virtual_die = obj.get_virtual_defense_die(target, source_ctx.dice)
                if virtual_die: break

        if virtual_die:
            def_ctx = self._create_roll_context(target, source_ctx.source, virtual_die)
            val_atk = source_ctx.final_value
            val_def = def_ctx.final_value
            res_str = f"🛡️Auto-Def {val_def} vs ⚔️{val_atk}"

            def_logs = "\n".join([f"• 🛡️ {target.name} (Auto): {l}" for l in def_ctx.log])

            result = ""
            if val_def > val_atk:
                self._handle_clash_win(def_ctx)
                self._handle_clash_lose(source_ctx)
                diff = max(0, val_def - val_atk)
                self._execute_clash_interaction(def_ctx, source_ctx, diff)
                result = f"{res_str} | **Defended!**"
            elif val_atk > val_def:
                self._handle_clash_win(source_ctx)
                self._handle_clash_lose(def_ctx)
                diff = max(0, val_atk - val_def)
                self._execute_clash_interaction(source_ctx, def_ctx, diff)
                result = f"{res_str} | **Defense Broken!**"
            else:
                result = f"{res_str} | Draw"
            return f"{result}\n{def_logs}"

        if source_ctx.dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            self._apply_damage(source_ctx, None, "hp")
            return "Unanswered Hit"
        return "Defensive Die (Skipped)"

    def _execute_clash_interaction(self, winner_ctx, loser_ctx, diff: int):
        interaction = self._calculate_standard_interaction(winner_ctx, loser_ctx, diff)
        self._dispatch_event("modify_clash_interaction", winner_ctx, interaction, loser_ctx)
        self._dispatch_event("modify_clash_interaction_loser", loser_ctx, interaction, winner_ctx)

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
        w_is_atk = w_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]
        l_is_atk = l_type in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]
        w_is_blk = w_type == DiceType.BLOCK
        w_is_evd = w_type == DiceType.EVADE

        result = {"action": "nothing", "dmg_type": "hp", "amount": 0, "target": loser_ctx.source,
                  "is_full_attack": False}

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