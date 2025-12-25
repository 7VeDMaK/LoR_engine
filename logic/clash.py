# logic/clash.py
import random
from core.models import Unit, Dice, DiceType
from logic.context import RollContext
from logic.status_definitions import STATUS_REGISTRY
from logic.card_scripts import SCRIPTS_REGISTRY


class ClashSystem:
    def __init__(self):
        self.logs = []

    def log(self, message):
        self.logs.append(message)

    # ==========================================
    # CORE LOOP
    # ==========================================
    def resolve_card_clash(self, attacker: Unit, defender: Unit):
        self.logs = []

        # 1. Начало боя (On Combat Start)
        self._trigger_unit_event("on_combat_start", attacker, self.log)
        self._trigger_unit_event("on_combat_start", defender, self.log)

        # 2. Расчет скорости
        speed_atk = self._calc_speed(attacker)
        speed_def = self._calc_speed(defender)
        diff = speed_atk - speed_def
        self.log(f"Speed: {attacker.name} ({speed_atk}) vs {defender.name} ({speed_def}). Diff: {diff}")

        # Определение преимуществ (Advantage)
        adv_attacker, adv_defender = self._get_advantage_state(diff)

        # Подготовка карт
        ac = attacker.current_card
        dc = defender.current_card
        if not ac or not dc:
            return [{"round": 0, "rolls": "No Card", "details": "Error"}]

        battle_report = []
        max_len = max(len(ac.dice_list), len(dc.dice_list))

        for i in range(max_len):
            # Проверка смерти/стаггера перед каждым кубиком
            if attacker.is_dead() or defender.is_dead():
                break
            if attacker.is_staggered():  # Оглушенный не бьет
                break

            die_a = ac.dice_list[i] if i < len(ac.dice_list) else None
            die_d = dc.dice_list[i] if i < len(dc.dice_list) else None

            # --- ФАЗА БРОСКА (ROLL PHASE) ---
            # Создаем контексты и запускаем событие on_roll (там считаются Сила, Паралич и т.д.)
            ctx_a = self._create_roll_context(attacker, defender, die_a, adv_attacker)
            ctx_d = self._create_roll_context(defender, attacker, die_d, adv_defender)

            # Значения для UI
            val_a = ctx_a.final_value if ctx_a else 0
            val_d = ctx_d.final_value if ctx_d else 0

            res_str = f"{attacker.name} [{val_a}] vs [{val_d}] {defender.name}"
            detail = ""

            # --- ФАЗА СРАВНЕНИЯ (CLASH PHASE) ---
            if ctx_a and ctx_d:
                if val_a > val_d:
                    detail = f"{attacker.name} Wins!"
                    self._handle_clash_win(ctx_a)
                    self._handle_clash_lose(ctx_d)

                    # Если не Evade - наносим урон
                    if ctx_a.dice.dtype != DiceType.EVADE:
                        self._apply_damage(ctx_a, ctx_d)

                elif val_d > val_a:
                    detail = f"{defender.name} Wins!"
                    self._handle_clash_win(ctx_d)
                    self._handle_clash_lose(ctx_a)

                    # Контратака защитника
                    if ctx_d.dice.dtype != DiceType.EVADE:
                        self._apply_damage(ctx_d, ctx_a)
                else:
                    detail = "Draw!"
                    # При ничьей обычно ничего не происходит, но можно добавить хук on_clash_draw

            elif ctx_a:
                # Односторонняя атака
                detail = "One-Sided Attack"
                self._apply_damage(ctx_a, None)  # None значит нет активной защиты

            # Запись логов статусов (если они писали в ctx.log)
            if ctx_a: self.logs.extend(ctx_a.log)
            if ctx_d: self.logs.extend(ctx_d.log)

            battle_report.append({"round": i + 1, "rolls": res_str, "details": detail})

        # 3. Конец боя (On Combat End)
        self._trigger_unit_event("on_combat_end", attacker, self.log)
        self._trigger_unit_event("on_combat_end", defender, self.log)

        return battle_report

    # ==========================================
    # HELPERS & EVENTS
    # ==========================================

    def _create_roll_context(self, source: Unit, target: Unit, die: Dice, advantage: str) -> RollContext:
        """
        Создает контекст, кидает базовый кубик (с учетом advantage)
        и применяет статус-эффекты (on_roll).
        """
        if not die:
            return None

        # 1. Базовая механика кубика (Advantage/Disadvantage)
        roll = random.randint(die.min_val, die.max_val)

        if advantage == "advantage":
            roll = max(roll, random.randint(die.min_val, die.max_val))
        elif advantage == "disadvantage":
            roll = min(roll, random.randint(die.min_val, die.max_val))
        elif advantage == "impossible":
            roll = 0

        # 2. Создаем контекст
        ctx = RollContext(source=source, target=target, dice=die, final_value=roll)

        # 3. Триггер событий on_roll (Сила, Паралич, Кровотечение при атаке)
        # Проходим по копии items, т.к. статусы могут меняться
        for status_id, stack in list(source.statuses.items()):
            if status_id in STATUS_REGISTRY:
                STATUS_REGISTRY[status_id].on_roll(ctx, stack)

        # 4. Скрипты самого кубика (например, "при мин. значении +5")
        # (Оставляем поддержку JSON-скриптов карты)
        self._process_card_scripts("on_roll", ctx)

        return ctx

    def _handle_clash_win(self, ctx: RollContext):
        """Триггерит on_clash_win для победителя"""
        for status_id, stack in list(ctx.source.statuses.items()):
            if status_id in STATUS_REGISTRY:
                STATUS_REGISTRY[status_id].on_clash_win(ctx, stack)
        self._process_card_scripts("on_clash_win", ctx)

    def _handle_clash_lose(self, ctx: RollContext):
        """Триггерит on_clash_lose для проигравшего"""
        for status_id, stack in list(ctx.source.statuses.items()):
            if status_id in STATUS_REGISTRY:
                STATUS_REGISTRY[status_id].on_clash_lose(ctx, stack)

    def _trigger_unit_event(self, event_name, unit, *args):
        """Универсальный триггер для событий уровня Юнита (Start/End Combat)"""
        for status_id, stack in list(unit.statuses.items()):
            if status_id in STATUS_REGISTRY:
                handler = getattr(STATUS_REGISTRY[status_id], event_name, None)
                if handler:
                    handler(unit, *args)  # Важно: тут сигнатура (unit, log_func)

    # ==========================================
    # DAMAGE CALCULATION
    # ==========================================
    def _apply_damage(self, attacker_ctx: RollContext, defender_ctx: RollContext):
        attacker = attacker_ctx.source
        defender = attacker_ctx.target  # Или брать из defender_ctx.source, если он есть

        if not defender:
            # Если это односторонняя атака, цель берем из контекста
            defender = attacker_ctx.target

        # 1. События On Hit (для атакующего - наложение статусов и т.д.)
        for status_id, stack in list(attacker.statuses.items()):
            if status_id in STATUS_REGISTRY:
                STATUS_REGISTRY[status_id].on_hit(attacker_ctx, stack)

        self._process_card_scripts("on_hit", attacker_ctx)

        # 2. Базовый урон
        raw_damage = attacker_ctx.final_value

        # Бонусы урона (Status Effects могут давать dmg_up/dmg_down)
        dmg_bonus = attacker.get_status("dmg_up") - attacker.get_status("dmg_down")
        raw_damage += dmg_bonus

        # 3. Резисты (HP и Stagger)
        dtype_name = attacker_ctx.dice.dtype.value.lower()  # slash, pierce, blunt
        res_hp = getattr(defender.hp_resists, dtype_name, 1.0)
        res_stagger = getattr(defender.stagger_resists, dtype_name, 1.0)

        # 4. Protection / Fragile (Входящий урон)
        incoming_mod = defender.get_status("fragile") + defender.get_status("vulnerability") - defender.get_status(
            "protection")

        # Итоговый расчет
        final_hp_dmg = int(raw_damage * res_hp) + incoming_mod
        final_hp_dmg = max(0, final_hp_dmg)

        final_stg_dmg = int(raw_damage * res_stagger)

        # 5. Барьер (Temp HP)
        barrier = defender.get_status("barrier")
        if barrier > 0:
            absorbed = min(barrier, final_hp_dmg)
            defender.remove_status("barrier", absorbed)
            final_hp_dmg -= absorbed
            self.log(f"🛡️ Barrier absorbed {absorbed} dmg")

        # Применение
        defender.current_hp -= final_hp_dmg
        defender.current_stagger -= final_stg_dmg

        self.log(f"💥 Hit! {defender.name} takes {final_hp_dmg} HP / {final_stg_dmg} Stagger")

    # ==========================================
    # UTILS
    # ==========================================
    def _calc_speed(self, unit: Unit) -> int:
        base = random.randint(1, 6)  # В будущем можно брать из unit.speed_range
        # Haste и Slow теперь просто статусы, которые мы читаем
        mod = unit.get_status("haste") - unit.get_status("slow")
        return max(1, base + mod)

    def _get_advantage_state(self, diff):
        adv_attacker = "normal"
        adv_defender = "normal"
        if diff >= 8:
            adv_defender = "impossible"
        elif diff >= 4:
            adv_defender = "disadvantage"
        elif diff <= -8:
            adv_attacker = "impossible"
        elif diff <= -4:
            adv_attacker = "disadvantage"
        return adv_attacker, adv_defender

    def _process_card_scripts(self, trigger: str, ctx: RollContext):
        """Обработка JSON-скриптов на самом кубике (старая система)"""
        die = ctx.dice
        if not die.scripts or trigger not in die.scripts:
            return

        for script_data in die.scripts[trigger]:
            script_id = script_data.get("script_id")
            params = script_data.get("params", {})
            if script_id in SCRIPTS_REGISTRY:
                SCRIPTS_REGISTRY[script_id](ctx, params)