# core/calculations.py
import math

# --- КОНСТАНТЫ ЭМОДЗИ (Чтобы легко менять) ---
ICO_STR = ""  # Сила (обычно кулак, но в логе пусто)
ICO_ATK = "🗡️"  # Мечи (Атака)
ICO_HP = "🤎"  # Коричневое сердечко (Здоровье)
ICO_BLK = "🛡️"  # Щит (Блок)
ICO_AGI = ""  # Ловкость
ICO_INIT = "👢"  # Сапог (Инициатива)
ICO_EVD = "🌀"  # Вихрь (Уклонение)
ICO_SP = "🧠"  # Мозг (Рассудок)
ICO_SLOT = "🧊"  # Куб (Слот дайса)
ICO_DMG = "💥"  # Взрыв (Урон)
ICO_HEAL = "💊"  # Таблетка (Лечение)


def recalculate_unit_stats(unit):
    logs = []
    mods = {
        "power_all": 0, "power_attack": 0, "power_block": 0, "power_evade": 0,
        "damage_deal": 0, "damage_take": 0, "heal_efficiency": 0.0, "initiative": 0,
        "power_light": 0, "power_medium": 0, "power_heavy": 0, "power_ranged": 0
    }

    # === 1. АТРИБУТЫ ===

    # СИЛА
    strength = unit.attributes.get("strength", 0)
    mod_str_3 = strength // 3
    if mod_str_3 != 0:
        logs.append(f"Повышает значение броска силы на {mod_str_3}")

    mod_str_5 = strength // 5
    if mod_str_5 != 0:
        mods["power_attack"] += mod_str_5
        logs.append(f"Повышает значение куба {ICO_ATK} атаки на атакующих картами на {mod_str_5}")

    # СТОЙКОСТЬ
    endurance = unit.attributes.get("endurance", 0)
    hp_percent_bonus = min(endurance * 2, 100)
    if hp_percent_bonus > 0:
        logs.append(f"Повышает максимальный показатель {ICO_HP} здоровья на {hp_percent_bonus}% от основного")

    hp_flat_bonus = (endurance // 3) * 5
    if hp_flat_bonus > 0:
        logs.append(f"Персонаж получает дополнительные {hp_flat_bonus} {ICO_HP} здоровья")

    mod_end_5 = endurance // 5
    if mod_end_5 != 0:
        mods["power_block"] += mod_end_5
        logs.append(f"Повышает значение куба {ICO_BLK} блока на {mod_end_5}")

    # ЛОВКОСТЬ
    agility = unit.attributes.get("agility", 0)
    mod_agi_3 = agility // 3
    if mod_agi_3 != 0:
        mods["initiative"] += mod_agi_3
        logs.append(f"Повышает значение броска ловкости и {ICO_INIT} инициативу на {mod_agi_3}")

    mod_agi_5 = agility // 5
    if mod_agi_5 != 0:
        mods["power_evade"] += mod_agi_5
        logs.append(f"Повышает значение куба {ICO_EVD} уклонения на {mod_agi_5}")

    # МУДРОСТЬ -> ИНТЕЛЛЕКТ
    wisdom = unit.attributes.get("wisdom", 0)
    bonus_int = wisdom // 3
    if bonus_int > 0:
        logs.append(f"Повышает значение интеллекта персонажа на основе его опыта.")

    # ПСИХИКА
    psych = unit.attributes.get("psych", 0)
    sp_percent_bonus = min(psych * 2, 100)
    if sp_percent_bonus > 0:
        logs.append(f"Повышает максимальный показатель {ICO_SP} рассудка на {sp_percent_bonus}% от основного")

    sp_flat_bonus = (psych // 3) * 5
    if sp_flat_bonus > 0:
        logs.append(f"Персонаж получает дополнительные {sp_flat_bonus} {ICO_SP} рассудка")

    if (psych // 3) > 0:
        logs.append(f"Повышает значение бросков против необъяснимого на {psych // 3}")

    # === 2. НАВЫКИ ===

    # Сила удара
    strike = unit.skills.get("strike_power", 0)
    mod_strike = strike // 3
    if mod_strike != 0:
        mods["damage_deal"] += mod_strike
        logs.append(f"Повышает показатель {ICO_DMG} урона при ударе на {mod_strike}")

    # Медицина
    med = unit.skills.get("medicine", 0)
    mod_med = med // 3
    if mod_med != 0:
        eff = mod_med * 10
        mods["heal_efficiency"] += (eff / 100.0)
        logs.append(f"Повышает бросок {ICO_HEAL} медицины на {mod_med}, эффективность лечения — {eff}%")

    # Сила воли (Stagger)
    will = unit.skills.get("willpower", 0)
    stagger_bonus_pct = min(will, 50)
    if stagger_bonus_pct > 0:
        logs.append(f"Повышает выдержку на {stagger_bonus_pct}%")

    # Удача
    luck = unit.skills.get("luck", 0)
    if luck > 0:
        logs.append(f"Повышает показатель удачи персонажа на {luck}")

    # Акробатика
    acro = unit.skills.get("acrobatics", 0)
    mod_acro = int((acro / 3) * 0.8)  # Округление вниз по условию
    if mod_acro > 0:
        mods["power_evade"] += mod_acro
        logs.append(f"Повышает значение куба {ICO_EVD} уклонения на {mod_acro}")

    # Щиты
    shields = unit.skills.get("shields", 0)
    mod_shields = math.ceil((shields / 3) * 0.8) if shields >= 3 else 0  # Округление ВВЕРХ по условию
    if mod_shields > 0:
        mods["power_block"] += mod_shields
        logs.append(f"Повышает значение куба {ICO_BLK} щита на {mod_shields}")

    # Оружие
    w_map = {
        "light_weapon": ("power_light", "лёгкого оружия"),
        "medium_weapon": ("power_medium", "среднего оружия"),
        "heavy_weapon": ("power_heavy", "тяжёлого оружия"),
        "firearms": ("power_ranged", "огнестрельного оружия")
    }
    for k, (mod_key, name_ru) in w_map.items():
        val = unit.skills.get(k, 0)
        bonus = val // 3
        if bonus != 0:
            mods[mod_key] += bonus
            logs.append(f"Повышает значение куба {ICO_ATK} удара атакующими картами {name_ru} на {bonus}")

    # Скорость
    spd_skill = unit.skills.get("speed", 0)

    # Инициатива (каждые 2 уровня)
    init_bonus_skill = spd_skill // 2
    if init_bonus_skill > 0:
        mods["initiative"] += init_bonus_skill
        logs.append(
            f"Повышает {ICO_INIT} инициативу последней доступной {ICO_SLOT} кости действия на {init_bonus_skill}")

    # Доп слот (каждые 10 уровней)
    extra_dice = spd_skill // 10
    unit.speed_dice_count = 1 + extra_dice
    if extra_dice > 0:
        logs.append(f"Вы получаете дополнительную {ICO_SLOT} кость действий (итого: {unit.speed_dice_count})")

    # Крепкая кожа
    skin = unit.skills.get("tough_skin", 0)
    mod_skin = int((skin / 3) * 1.2)  # Округление вниз
    if mod_skin > 0:
        mods["damage_take"] -= mod_skin
        logs.append(f"Понижает получаемый урон на {mod_skin}")

    # Красноречие
    elo = unit.skills.get("eloquence", 0)
    if elo > 0:
        logs.append(f"Повышает значение броска при убеждении, запугивании, обмане или торговле на {elo}")

    # Ковка
    forg = unit.skills.get("forging", 0)
    if forg > 0: logs.append(f"Повышает бросок качества созданного предмета на {forg}")

    # Инженерия
    eng = unit.skills.get("engineering", 0)
    if eng > 0: logs.append(f"Повышает значение броска при определении качества объекта на {eng}")

    # Программирование
    prog = unit.skills.get("programming", 0)
    if prog > 0: logs.append(f"Повышает значение успешного взлома на {prog}")

    # === ИТОГОВЫЕ РАСЧЕТЫ СТАТОВ ===

    # 1. HP
    base_hp = 20
    hp_rolls = sum(5 + v.get("hp", 0) for v in unit.level_rolls.values())

    # Формула: (Base + Rolls + FlatEnd) * End% * Implant% * Talent%
    raw_hp = base_hp + hp_rolls + hp_flat_bonus
    buff_end_mult = 1 + (hp_percent_bonus / 100.0)
    hp_step1 = raw_hp * buff_end_mult
    hp_step2 = hp_step1 * (1 + unit.implants_hp_pct / 100.0)
    final_hp = hp_step2 * (1 + unit.talents_hp_pct / 100.0)
    unit.max_hp = int(final_hp)

    # 2. SP
    base_sp = 20
    sp_rolls = sum(5 + v.get("sp", 0) for v in unit.level_rolls.values())

    raw_sp = base_sp + sp_rolls + sp_flat_bonus
    buff_psy_mult = 1 + (sp_percent_bonus / 100.0)
    sp_step1 = raw_sp * buff_psy_mult
    sp_step2 = sp_step1 * (1 + unit.implants_sp_pct / 100.0)
    final_sp = sp_step2 * (1 + unit.talents_sp_pct / 100.0)
    unit.max_sp = int(final_sp)

    # 3. STAGGER
    # База = 50% от HP. Бонус = Сила Воли %
    base_stagger = unit.max_hp // 2
    final_stagger = base_stagger * (1 + stagger_bonus_pct / 100.0)
    unit.max_stagger = int(final_stagger)

    # 4. SPEED
    unit.speed_min = unit.base_speed_min + mods["initiative"]
    unit.speed_max = unit.base_speed_max + mods["initiative"]

    # Limits
    unit.current_hp = min(unit.current_hp, unit.max_hp)
    unit.current_sp = min(unit.current_sp, unit.max_sp)
    unit.current_stagger = min(unit.current_stagger, unit.max_stagger)

    unit.modifiers = mods
    return logs