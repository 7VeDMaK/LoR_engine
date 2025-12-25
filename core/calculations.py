import math

# Эмодзи
I_ATK, I_HP, I_BLK = "⬆", "🤎", "🛡️"
I_INIT, I_EVD, I_SP, I_DICE = "👢", "🌀", "🧠", "🧊"


def recalculate_unit_stats(unit):
    logs = []
    mods = {
        "power_all": 0, "power_attack": 0, "power_block": 0, "power_evade": 0,
        "damage_deal": 0, "damage_take": 0, "heal_efficiency": 0.0, "initiative": 0,
        "power_light": 0, "power_medium": 0, "power_heavy": 0, "power_ranged": 0
    }

    # === 1. АТРИБУТЫ ===
    strength = unit.attributes.get("strength", 0)
    if (strength // 3) != 0: logs.append(f"Повышает значение броска силы на {strength // 3}")
    if (strength // 5) != 0:
        mods["power_attack"] += strength // 5
        logs.append(f"Повышает значение куба {I_ATK} атаки на {strength // 5}")

    endurance = unit.attributes.get("endurance", 0)
    hp_flat = (endurance // 3) * 5
    hp_pct = min(endurance * 2, 100)
    if hp_pct > 0: logs.append(f"Повышает макс {I_HP} здоровья на {hp_pct}%")
    if hp_flat > 0: logs.append(f"Персонаж получает +{hp_flat} {I_HP} здоровья")
    if (endurance // 5) != 0:
        mods["power_block"] += endurance // 5
        logs.append(f"Повышает значение куба {I_BLK} блока на {endurance // 5}")

    agility = unit.attributes.get("agility", 0)
    if (agility // 3) != 0:
        mods["initiative"] += agility // 3
        logs.append(f"Повышает {I_INIT} инициативу на {agility // 3}")
    if (agility // 5) != 0:
        mods["power_evade"] += agility // 5
        logs.append(f"Повышает значение куба {I_EVD} уклонения на {agility // 5}")

    wisdom = unit.attributes.get("wisdom", 0)
    if (wisdom // 3) > 0: logs.append("Повышает значение интеллекта (опыт).")

    psych = unit.attributes.get("psych", 0)
    sp_flat = (psych // 3) * 5
    sp_pct = min(psych * 2, 100)
    if sp_pct > 0: logs.append(f"Повышает макс {I_SP} рассудка на {sp_pct}%")
    if sp_flat > 0: logs.append(f"Персонаж получает +{sp_flat} {I_SP} рассудка")
    if (psych // 3) > 0: logs.append(f"Повышает броски против необъяснимого на {psych // 3}")

    # === 2. НАВЫКИ ===
    strike = unit.skills.get("strike_power", 0)
    if (strike // 3) != 0:
        mods["damage_deal"] += strike // 3
        logs.append(f"Повышает урон при ударе на {strike // 3}")

    med = unit.skills.get("medicine", 0)
    if (med // 3) != 0:
        eff = med * 10;
        mods["heal_efficiency"] += eff / 100.0
        logs.append(f"Повышает лечение на {eff}%")

    will = unit.skills.get("willpower", 0)
    stg_pct = min(will, 50)
    if stg_pct > 0: logs.append(f"Повышает выдержку на {stg_pct}%")

    luck = unit.skills.get("luck", 0)
    if luck > 0: logs.append(f"Повышает удачу на {luck}")

    acro = unit.skills.get("acrobatics", 0)
    mod_acro = int((acro / 3) * 0.8)
    if mod_acro > 0:
        mods["power_evade"] += mod_acro
        logs.append(f"Повышает уклонение на {mod_acro}")

    shields = unit.skills.get("shields", 0)
    mod_shields = math.ceil((shields / 3) * 0.8) if shields >= 3 else 0
    if mod_shields > 0:
        mods["power_block"] += mod_shields
        logs.append(f"Повышает щит на {mod_shields}")

    w_map = {"light_weapon": "лёгкого", "medium_weapon": "среднего", "heavy_weapon": "тяжёлого",
             "firearms": "огнестрельного"}
    for k, name in w_map.items():
        v = unit.skills.get(k, 0)
        if (v // 3) != 0:
            mods[f"power_{k.split('_')[0]}"] += v // 3
            logs.append(f"Повышает атаку {name} оружия на {v // 3}")

    spd = unit.skills.get("speed", 0)

    # 1. Определяем количество кубиков
    # База 1. +1 на 10, 20, 30 уровнях навыка.
    dice_count = 1
    if spd >= 10: dice_count += 1
    if spd >= 20: dice_count += 1
    if spd >= 30: dice_count += 1

    final_dice = []

    # Глобальный бонус от Ловкости (уже лежит в mods["initiative"])
    # Навык скорости СЮДА НЕ ДОБАВЛЯЕТСЯ, он считается для каждого куба отдельно
    global_init_bonus = mods["initiative"]

    for i in range(dice_count):
        # Рассчитываем бонус навыка для КОНКРЕТНОГО кубика
        skill_bonus = 0

        # Спец. условие для 4-го кубика на 30 уровне: он сразу фулловый (+5)
        if i == 3 and spd >= 30:
            skill_bonus = 5
        else:
            # Обычная логика: сколько очков навыка вложено в этот "тир" (0-10)
            # Кубик 1 (i=0): берет уровни 1-10
            # Кубик 2 (i=1): берет уровни 11-20
            # Кубик 3 (i=2): берет уровни 21-30
            points_in_tier = max(0, min(10, spd - (i * 10)))
            skill_bonus = points_in_tier // 2

        # Итоговая формула для конкретного кубика
        # База (1~4) + Глобал (Ловкость) + Навык (Специфичный для куба)
        d_min = unit.base_speed_min + global_init_bonus + skill_bonus
        d_max = unit.base_speed_max + global_init_bonus + skill_bonus

        final_dice.append((d_min, d_max))

    unit.computed_speed_dice = final_dice
    unit.speed_dice_count = dice_count

    # Лог только о новых слотах, так как значения разные
    if (spd // 10) > 0:
        logs.append(f"Вы получаете дополнительную {I_DICE} кость действий (итого: {dice_count})")

    # Кожа
    skin = unit.skills.get("tough_skin", 0)
    m_skin = int((skin / 3) * 1.2)
    if m_skin > 0:
        mods["damage_take"] -= m_skin
        logs.append(f"Понижает получаемый урон на {m_skin}")

    # Социальные
    elo = unit.skills.get("eloquence", 0)
    if elo > 0: logs.append(f"Повышает убеждение/торговлю на {elo}")
    forg = unit.skills.get("forging", 0)
    if forg > 0: logs.append(f"Повышает ковку на {forg}")
    eng = unit.skills.get("engineering", 0)
    if eng > 0: logs.append(f"Повышает инженерию на {eng}")
    prog = unit.skills.get("programming", 0)
    if prog > 0: logs.append(f"Повышает взлом на {prog}")

    # === ИТОГОВЫЕ СТАТЫ ===
    # HP
    base_h = 20
    rolls_h = sum(5 + v.get("hp", 0) for v in unit.level_rolls.values())
    raw_h = base_h + rolls_h + hp_flat

    # Строчка расчета Имплантов (ты просил):
    # health_step2 = health_step1 * (1 + unit.implants_hp_pct / 100.0)

    step1 = raw_h * (1 + hp_pct / 100.0)
    step2 = step1 * (1 + unit.implants_hp_pct / 100.0)  # <--- ВОТ ИМПЛАНТЫ
    final_h = step2 * (1 + unit.talents_hp_pct / 100.0)
    unit.max_hp = int(final_h)

    # SP
    base_s = 20
    rolls_s = sum(5 + v.get("sp", 0) for v in unit.level_rolls.values())
    raw_s = base_s + rolls_s + sp_flat

    step1_s = raw_s * (1 + sp_pct / 100.0)
    step2_s = step1_s * (1 + unit.implants_sp_pct / 100.0)  # <--- ИМПЛАНТЫ SP
    final_s = step2_s * (1 + unit.talents_sp_pct / 100.0)
    unit.max_sp = int(final_s)

    # STAGGER
    base_stg = unit.max_hp // 2
    final_stg = base_stg * (1 + stg_pct / 100.0)
    unit.max_stagger = int(final_stg)

    unit.current_hp = min(unit.current_hp, unit.max_hp)
    unit.current_sp = min(unit.current_sp, unit.max_sp)
    unit.current_stagger = min(unit.current_stagger, unit.max_stagger)

    unit.modifiers = mods
    return logs