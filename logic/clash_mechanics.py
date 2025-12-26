import random
from core.models import Dice, DiceType
from logic.context import RollContext
from logic.status_definitions import STATUS_REGISTRY
from logic.card_scripts import SCRIPTS_REGISTRY
from logic.passives import PASSIVE_REGISTRY
from logic.talents import TALENT_REGISTRY


class ClashMechanicsMixin:
    """
    Уровень 1: Низкоуровневая механика.
    Отвечает за броски, подсчет модификаторов и нанесение урона.
    Теперь с подробными логами!
    """

    def _dispatch_event(self, event_name: str, context: RollContext, *args):
        """Универсальный диспетчер событий."""
        unit = context.source

        # 1. Статусы
        for status_id, stack in list(unit.statuses.items()):
            if status_id in STATUS_REGISTRY:
                handler = getattr(STATUS_REGISTRY[status_id], event_name, None)
                if handler: handler(context, stack, *args)

        # 2. Пассивки
        for pid in unit.passives:
            if pid in PASSIVE_REGISTRY:
                handler = getattr(PASSIVE_REGISTRY[pid], event_name, None)
                if handler: handler(context, *args)

        # 3. Таланты
        for tid in unit.talents:
            if tid in TALENT_REGISTRY:
                handler = getattr(TALENT_REGISTRY[tid], event_name, None)
                if handler: handler(context, *args)

        # 4. Скрипты карты
        self._process_card_scripts(event_name, context)

    def _process_card_scripts(self, trigger: str, ctx: RollContext):
        die = ctx.dice
        if not die or not die.scripts or trigger not in die.scripts: return
        for script_data in die.scripts[trigger]:
            script_id = script_data.get("script_id")
            params = script_data.get("params", {})
            if script_id in SCRIPTS_REGISTRY: SCRIPTS_REGISTRY[script_id](ctx, params)

    def _process_card_self_scripts(self, trigger: str, source, target):
        card = source.current_card
        if not card or not card.scripts or trigger not in card.scripts: return
        ctx = RollContext(source=source, target=target, dice=None, final_value=0, log=self.logs)
        for script_data in card.scripts[trigger]:
            script_id = script_data.get("script_id")
            params = script_data.get("params", {})
            if script_id in SCRIPTS_REGISTRY: SCRIPTS_REGISTRY[script_id](ctx, params)

    def _create_roll_context(self, source, target, die: Dice) -> RollContext:
        if not die: return None
        roll = random.randint(die.min_val, die.max_val)
        ctx = RollContext(source=source, target=target, dice=die, final_value=roll)

        # Мы добавляем описание кубика в лог сразу, чтобы было понятно
        ctx.log.append(f"🎲 Roll [{die.min_val}-{die.max_val}]: **{roll}**")

        # === ДЕТАЛИЗАЦИЯ БОНУСОВ ===
        mods = source.modifiers

        if die.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]:
            # Сила (Power Attack хранит бонус от силы)
            str_bonus = mods.get("power_attack", 0)
            if str_bonus: ctx.modify_power(str_bonus, "Сила")

            # Навык оружия (Для простоты считаем Medium, в идеале брать тип карты)
            skill_bonus = mods.get("power_medium", 0)
            if skill_bonus: ctx.modify_power(skill_bonus, "Навык")

        elif die.dtype == DiceType.BLOCK:
            # Стойкость + Щиты
            blk_bonus = mods.get("power_block", 0)
            if blk_bonus: ctx.modify_power(blk_bonus, "Стойкость/Щит")

        elif die.dtype == DiceType.EVADE:
            # Ловкость + Акробатика
            evd_bonus = mods.get("power_evade", 0)
            if evd_bonus: ctx.modify_power(evd_bonus, "Ловк/Акробатика")

        # Вызываем события (статусы, пассивки могут добавить свои бонусы)
        self._dispatch_event("on_roll", ctx)

        return ctx

    def _handle_clash_win(self, ctx: RollContext):
        self._dispatch_event("on_clash_win", ctx)

    def _handle_clash_lose(self, ctx: RollContext):
        self._dispatch_event("on_clash_lose", ctx)

    def _trigger_unit_event(self, event_name, unit, *args):
        # Версия без контекста броска
        for status_id, stack in list(unit.statuses.items()):
            if status_id in STATUS_REGISTRY:
                handler = getattr(STATUS_REGISTRY[status_id], event_name, None)
                if handler: handler(unit, *args)

        for pid in unit.passives:
            if pid in PASSIVE_REGISTRY:
                handler = getattr(PASSIVE_REGISTRY[pid], event_name, None)
                if handler: handler(unit, *args)

        for pid in unit.talents:
            if pid in TALENT_REGISTRY:
                handler = getattr(TALENT_REGISTRY[pid], event_name, None)
                if handler: handler(unit, *args)

    # === УЛУЧШЕННЫЙ ЛОГ УРОНА ===

    def _deal_direct_damage(self, source_ctx: RollContext, target, amount: int, dmg_type: str):
        if amount <= 0: return

        if dmg_type == "hp":
            dtype_name = source_ctx.dice.dtype.value.lower()
            res = getattr(target.hp_resists, dtype_name, 1.0)

            # Проверяем стаггер
            is_stag_hit = False
            if target.is_staggered():
                res *= 2.0
                is_stag_hit = True

            final_dmg = int(amount * res)

            # Барьер
            barrier = target.get_status("barrier")
            if barrier > 0:
                absorbed = min(barrier, final_dmg)
                target.remove_status("barrier", absorbed)
                final_dmg -= absorbed
                source_ctx.log.append(f"🛡️ Барьер поглотил {absorbed} урона")

            target.current_hp -= final_dmg

            # ФОРМИРУЕМ ПОНЯТНЫЙ ЛОГ
            msg = f"💥 **Попадание!** {target.name} получает **{final_dmg}** урона"
            if res != 1.0:
                msg += f" (Resist x{res:.1f})"
            if is_stag_hit:
                msg += " [STAGGER x2]"

            source_ctx.log.append(msg)

        elif dmg_type == "stagger":
            dtype_name = source_ctx.dice.dtype.value.lower()
            res = getattr(target.stagger_resists, dtype_name, 1.0)
            final_dmg = int(amount * res)

            target.current_stagger -= final_dmg
            source_ctx.log.append(f"😵 Урон по Stagger: **{final_dmg}** (по {target.name})")

    def _apply_damage(self, attacker_ctx: RollContext, defender_ctx: RollContext, dmg_type: str = "hp"):
        attacker = attacker_ctx.source
        defender = attacker_ctx.target or attacker_ctx.target

        self._dispatch_event("on_hit", attacker_ctx)

        raw_damage = attacker_ctx.final_value

        # Собираем модификаторы для лога
        dmg_bonus = attacker.get_status("dmg_up") - attacker.get_status("dmg_down")
        dmg_bonus += attacker.modifiers.get("damage_deal", 0)

        incoming_mod = defender.get_status("fragile") + defender.get_status("vulnerability") - defender.get_status(
            "protection")
        incoming_mod -= defender.modifiers.get("damage_take", 0)

        total_amt = max(0, raw_damage + dmg_bonus + incoming_mod)

        # Если были модификаторы урона, можно добавить инфо
        # if dmg_bonus != 0: attacker_ctx.log.append(f"[Dmg Bonus: {dmg_bonus}]")

        if attacker_ctx.damage_multiplier != 1.0:
            total_amt = int(total_amt * attacker_ctx.damage_multiplier)
            attacker_ctx.log.append(f"⚡ Крит множитель x{attacker_ctx.damage_multiplier}!")

        self._deal_direct_damage(attacker_ctx, defender, total_amt, dmg_type)

        if dmg_type == "hp" and not defender.is_staggered():
            dtype_name = attacker_ctx.dice.dtype.value.lower()
            res_stagger = getattr(defender.stagger_resists, dtype_name, 1.0)
            stg_dmg = int(total_amt * res_stagger)
            defender.current_stagger -= stg_dmg