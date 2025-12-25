# logic/clash.py
import random
from core.models import Unit, Card, Dice, DiceType
from logic.card_scripts import SCRIPTS_REGISTRY
from logic.modifiers import RollContext


class ClashSystem:
    def __init__(self):
        self.logs = []

    def log(self, message):
        self.logs.append(message)

    def resolve_card_clash(self, attacker: Unit, defender: Unit):
        self.logs = []
        round_num = 1

        # 0. Считаем скорость (для определения помех)
        speed_atk = self._calc_speed(attacker)
        speed_def = self._calc_speed(defender)

        # Разница скоростей (твоя механика помех)
        diff = speed_atk - speed_def
        adv_attacker = "normal"  # normal, advantage, disadvantage, impossible
        adv_defender = "normal"

        if diff >= 8:
            adv_defender = "impossible"
        elif diff >= 4:
            adv_defender = "disadvantage"
        elif diff <= -8:
            adv_attacker = "impossible"
        elif diff <= -4:
            adv_attacker = "disadvantage"

        self.log(f"Speed: {attacker.name} ({speed_atk}) vs {defender.name} ({speed_def}). Diff: {diff}")

        # Основной цикл кубиков
        # (Упрощенно: берем макс кол-во кубиков, как раньше)
        ac = attacker.current_card
        dc = defender.current_card

        if not ac or not dc:
            return [{"round": 0, "rolls": "No Card", "details": "Error"}]

        # Обработка "Бей и беги" (Stealth) - сброс при атаке
        if attacker.get_status("stealth"):
            attacker.remove_status("stealth")
            self.log(f"👻 {attacker.name} revealed from Stealth!")

        max_len = max(len(ac.dice_list), len(dc.dice_list))
        battle_report = []

        for i in range(max_len):
            # Если кто-то оглушен или мертв - бой односторонний или конец
            if attacker.is_staggered() or attacker.is_dead() or defender.is_dead():
                break

            die_a = ac.dice_list[i] if i < len(ac.dice_list) else None
            die_d = dc.dice_list[i] if i < len(dc.dice_list) else None

            # --- БРОСКИ (С учетом Силы/Слабости/Паралича) ---
            val_a = 0
            val_d = 0

            if die_a:
                val_a = self._roll_die(attacker, die_a, adv_attacker)
                # Триггер Кровотечения (При атаке)
                if die_a.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
                    self._trigger_bleed(attacker)

            if die_d:
                val_d = self._roll_die(defender, die_d, adv_defender)
                # Триггер Глубокой раны (При защите)
                if die_d.dtype in [DiceType.BLOCK, DiceType.EVADE]:
                    self._trigger_deep_wound(defender)

            # Лог броска
            res_str = f"{attacker.name} [{val_a}] vs [{val_d}] {defender.name}"

            detail = ""

            # --- СРАВНЕНИЕ (CLASH) ---
            if die_a and die_d:
                if val_a > val_d:
                    detail = f"{attacker.name} Wins!"
                    # Обработка Уклонения (если победил уклонением - урон не наносится)
                    if die_a.dtype == DiceType.EVADE:
                        pass
                    else:
                        self._apply_damage(attacker, defender, die_a, val_a)
                elif val_d > val_a:
                    detail = f"{defender.name} Wins!"
                    # Контр-атака защитника (если у него атака)
                    if die_d.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
                        self._apply_damage(defender, attacker, die_d, val_d)
                    # Если у защитника блок - он поглотил урон (урон 0)
                else:
                    detail = "Draw!"
            elif die_a:
                # Односторонняя атака
                detail = "One-Sided Attack"
                self._apply_damage(attacker, defender, die_a, val_a)

            battle_report.append({"round": i + 1, "rolls": res_str, "details": detail})

        return battle_report

    def _process_scripts(self, trigger: str, attacker: Unit, defender: Unit, die: Dice, roll_val: int):
        """
        Проверяет, есть ли на кубике скрипты для заданного триггера (например, 'on_hit')
        и выполняет их.
        """
        if not die.scripts or trigger not in die.scripts:
            return

        # Создаем контекст для скрипта
        ctx = RollContext(source=attacker, target=defender, dice=die, final_value=roll_val, log=self.logs)

        # Перебираем все скрипты для этого триггера
        for script_data in die.scripts[trigger]:
            script_id = script_data.get("script_id")
            params = script_data.get("params", {})

            if script_id in SCRIPTS_REGISTRY:
                # Вызываем функцию из реестра
                SCRIPTS_REGISTRY[script_id](ctx, params)

    def _calc_speed(self, unit: Unit) -> int:
        # Базовая скорость (допустим, кидаем d6) + Haste - Slow
        base = random.randint(1, 6)  # Или брать из unit.speed_range
        mod = unit.get_status("haste") - unit.get_status("slow")
        return max(1, base + mod)

    def _roll_die(self, unit: Unit, die: Dice, advantage: str) -> int:
        # 1. Проверка Паралича
        paralysis = unit.get_status("paralysis")
        if paralysis > 0:
            unit.remove_status("paralysis", 1)
            return die.min_val  # Фиксируем на минимуме

        # 2. Базовый бросок
        roll = random.randint(die.min_val, die.max_val)

        # Если помеха/преимущество (от скорости)
        if advantage == "advantage":
            roll = max(roll, random.randint(die.min_val, die.max_val))
        elif advantage == "disadvantage":
            roll = min(roll, random.randint(die.min_val, die.max_val))
        elif advantage == "impossible":
            return 0  # Не может атаковать

        # 3. Модификаторы (Сила/Стойкость)
        bonus = 0
        if die.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            bonus += unit.get_status("strength")
            bonus -= unit.get_status("weakness")
        elif die.dtype in [DiceType.BLOCK, DiceType.EVADE]:
            bonus += unit.get_status("endurance")
            bonus -= unit.get_status("disarm")

        return max(0, roll + bonus)

    def _trigger_bleed(self, unit: Unit):
        bleed = unit.get_status("bleed")
        if bleed > 0:
            # Урон равен стакам
            unit.current_hp -= bleed
            # Уполовиниваем (округляем вниз)
            unit.statuses["bleed"] = bleed // 2
            self.log(f"🩸 {unit.name} takes {bleed} Bleed dmg!")

    def _trigger_deep_wound(self, unit: Unit):
        dw = unit.get_status("deep_wound")
        if dw > 0:
            unit.current_hp -= dw
            unit.add_status("bleed", dw)  # Превращаем в кровоток
            self.log(f"💔 Deep Wound: {unit.name} takes {dw} dmg -> Bleed")

    def _apply_damage(self, attacker: Unit, defender: Unit, die: Dice, roll_val: int):
        # 1. Расчет базового урона (ролл + бонусы)
        dmg_bonus = attacker.get_status("dmg_up") - attacker.get_status("dmg_down")
        self._process_scripts("on_hit", attacker, defender, die, roll_val)
        # Ритм (1 урона за 2 ритма)
        rhythm = attacker.get_status("rhythm")
        dmg_bonus += rhythm // 2

        raw_damage = roll_val + dmg_bonus

        # 2. Критический удар (Самообладание)
        is_crit = False
        poise = attacker.get_status("poise")
        if poise > 0:
            crit_chance = poise * 5  # 5% за стак
            if random.randint(1, 100) <= crit_chance:
                is_crit = True
                raw_damage *= 2
                attacker.remove_status("poise", 20)
                self.log("💥 CRITICAL HIT!")

        # 3. Резисты (HP и Stagger)
        res_hp = getattr(defender.hp_resists, die.dtype.value.lower(), 1.0)
        res_stagger = getattr(defender.stagger_resists, die.dtype.value.lower(), 1.0)

        # Уязвимость (Vulnerability) понижает резист? Или просто добавляет урон?
        # В ТЗ: "понижает защиту". Будем считать, что это аналог Fragile (доп урон).

        # 4. Fragile / Protection (Плоский модификатор входящего)
        incoming_mod = defender.get_status("fragile") + defender.get_status("vulnerability") - defender.get_status(
            "protection")

        final_hp_dmg = int(raw_damage * res_hp) + incoming_mod
        final_hp_dmg = max(0, final_hp_dmg)  # Не лечим уроном

        final_stg_dmg = int(raw_damage * res_stagger)

        # Барьер (Temp HP)
        barrier = defender.get_status("barrier")
        if barrier > 0:
            absorbed = min(barrier, final_hp_dmg)
            defender.remove_status("barrier", absorbed)
            final_hp_dmg -= absorbed
            self.log(f"🛡️ Barrier absorbed {absorbed} dmg")

        # Нанесение
        defender.current_hp -= final_hp_dmg
        defender.current_stagger -= final_stg_dmg

        self.log(f"Hit! {defender.name} takes {final_hp_dmg} HP / {final_stg_dmg} Stagger dmg.")

        # --- ON HIT ЭФФЕКТЫ ---

        # Разрыв (Rupture) - чистый урон
        rup = defender.get_status("rupture")
        if rup > 0:
            defender.current_hp -= rup
            defender.statuses["rupture"] = max(0, rup // 2)  # Половина
            self.log(f"💥 Rupture: {rup} true dmg")

        # Утопание (Sinking) - урон рассудку
        sink = defender.get_status("sinking")
        if sink > 0:
            defender.take_sanity_damage(sink)
            defender.statuses["sinking"] = max(0, sink // 2)
            self.log(f"🧠 Sinking: {sink} SP dmg")

        # Попадание по ритму (теряет 1 ритм при получении урона)
        if defender.get_status("rhythm") > 0:
            defender.remove_status("rhythm", 1)

        # Скрипты карты (Dice effects) - вызов через реестр
        # (Этот код у нас уже был в logic/card_scripts.py, тут просто напоминание)
        if die.scripts:
            pass  # Тут вызов скриптов как раньше