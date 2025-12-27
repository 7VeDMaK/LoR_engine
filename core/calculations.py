import math
from logic.passives import PASSIVE_REGISTRY
from logic.talents import TALENT_REGISTRY

# Эмодзи
I_ATK, I_HP, I_BLK = "⬆", "🤎", "🛡️"
I_INIT, I_EVD, I_SP, I_DICE = "👢", "🌀", "🧠", "🧊"


def recalculate_unit_stats(unit):
    logs = []

    # Инициализация
    mods = {
        "power_all": 0, "power_attack": 0, "power_block": 0, "power_evade": 0,
        "damage_deal": 0, "damage_take": 0, "heal_efficiency": 0.0, "initiative": 0,
        "power_light": 0, "power_medium": 0, "power_heavy": 0, "power_ranged": 0,
        "total_intellect": 0, "max_sp_pct": 0
    }

    # Сбор всех ключей
    all_stat_keys = list(unit.attributes.keys()) + list(unit.skills.keys())
    all_stat_keys.append("bonus_intellect")
    bonuses = {k: 0 for k in all_stat_keys}

    # Сбор способностей
    abilities = []
    for pid in unit.passives:
        if pid in PASSIVE_REGISTRY: abilities.append(PASSIVE_REGISTRY[pid])
    for pid in unit.talents:
        if pid in TALENT_REGISTRY: abilities.append(TALENT_REGISTRY[pid])

    # Статусы тоже могут влиять на on_calculate_stats (например, Red Lycoris)
    # Нам нужно достать классы статусов
    from logic.status_definitions import STATUS_REGISTRY
    for status_id, stack in unit.statuses.items():
        if status_id in STATUS_REGISTRY and stack > 0:
            st_obj = STATUS_REGISTRY[status_id]
            # Проверяем, есть ли у статуса метод для статов
            if hasattr(st_obj, 'on_calculate_stats'):
                s_bonuses = st_obj.on_calculate_stats(unit)
                for k, v in s_bonuses.items():
                    if k in mods:
                        mods[k] += v
                    # Если статус дает статы (редко, но бывает)
                    elif k in bonuses:
                        bonuses[k] += v

    # Суммируем бонусы талантов
    for ab in abilities:
        ab_bonuses = ab.on_calculate_stats(unit)
        for stat, val in ab_bonuses.items():
            if stat in bonuses:
                bonuses[stat] += val
            elif stat in mods:
                # Вот здесь сработает: mods["max_sp_pct"] += 20
                mods[stat] += val
            elif stat == "backstab_deal":
                mods["damage_deal"] += val
            elif stat == "backstab_take":
                mods["damage_take"] += abs(val)

    # Helper
    def get_total(container, key):
        base = container.get(key, 0)
        bonus = bonuses.get(key, 0)
        total = base + bonus
        mods[f"total_{key}"] = total
        return total

    # АТРИБУТЫ
    strength = get_total(unit.attributes, "strength")
    endurance = get_total(unit.attributes, "endurance")
    agility = get_total(unit.attributes, "agility")
    wisdom = get_total(unit.attributes, "wisdom")
    psych = get_total(unit.attributes, "psych")

    # ИНТЕЛЛЕКТ
    total_intellect = unit.base_intellect + bonuses["bonus_intellect"] + (wisdom // 3)
    mods["total_intellect"] = total_intellect

    # НАВЫКИ
    strike = get_total(unit.skills, "strike_power")
    med = get_total(unit.skills, "medicine")
    will = get_total(unit.skills, "willpower")
    luck = get_total(unit.skills, "luck")
    acro = get_total(unit.skills, "acrobatics")
    shields = get_total(unit.skills, "shields")
    skin = get_total(unit.skills, "tough_skin")
    spd = get_total(unit.skills, "speed")

    elo = get_total(unit.skills, "eloquence")
    forg = get_total(unit.skills, "forging")
    eng = get_total(unit.skills, "engineering")
    prog = get_total(unit.skills, "programming")

    # Оружие
    w_light = get_total(unit.skills, "light_weapon")
    w_med = get_total(unit.skills, "medium_weapon")
    w_heavy = get_total(unit.skills, "heavy_weapon")
    w_fire = get_total(unit.skills, "firearms")

    # === ЭФФЕКТЫ ===

    # Strength
    if (strength // 5) > 0:
        mods["power_attack"] += strength // 5
        logs.append(f"Сила: +{strength // 5} Atk Power")

    # Endurance
    hp_flat = (endurance // 3) * 5
    hp_pct = min(endurance * 2, 100)
    if (endurance // 5) > 0:
        mods["power_block"] += endurance // 5
        logs.append(f"Стойкость: +{endurance // 5} Block Power")

    # Agility
    if (agility // 3) > 0:
        mods["initiative"] += agility // 3
    if (agility // 5) > 0:
        mods["power_evade"] += agility // 5
        logs.append(f"Ловкость: +{agility // 5} Evade Power")

    # Psych
    sp_flat = (psych // 3) * 5
    sp_pct = min(psych * 2, 100)

    # --- Skills ---
    if (strike // 3) > 0:
        mods["damage_deal"] += strike // 3
        logs.append(f"Сила удара: +{strike // 3} dmg")

    if (med // 3) > 0:
        eff = med * 10
        mods["heal_efficiency"] += eff / 100.0

    stg_pct = min(will, 50)

    mod_acro = int((acro / 3) * 0.8)
    if mod_acro > 0:
        mods["power_evade"] += mod_acro

    mod_shields = math.ceil((shields / 3) * 0.8) if shields >= 3 else 0
    if mod_shields > 0:
        mods["power_block"] += mod_shields

    if (w_light // 3) > 0: mods["power_light"] += w_light // 3
    if (w_med // 3) > 0: mods["power_medium"] += w_med // 3
    if (w_heavy // 3) > 0: mods["power_heavy"] += w_heavy // 3
    if (w_fire // 3) > 0: mods["power_ranged"] += w_fire // 3

    # Speed
    dice_count = 1
    if spd >= 10: dice_count += 1
    if spd >= 20: dice_count += 1
    if spd >= 30: dice_count += 1

    final_dice = []
    global_init = mods["initiative"]

    for i in range(dice_count):
        skill_bonus = 0
        if i == 3 and spd >= 30:
            skill_bonus = 5
        else:
            points = max(0, min(10, spd - (i * 10)))
            skill_bonus = points // 2
        d_min = unit.base_speed_min + global_init + skill_bonus
        d_max = unit.base_speed_max + global_init + skill_bonus
        final_dice.append((d_min, d_max))

    unit.computed_speed_dice = final_dice
    unit.speed_dice_count = dice_count

    # === ИСПРАВЛЕНИЕ КОЖИ (Tough Skin) ===
    # Раньше было -=, теперь += (увеличиваем "поглощение")
    m_skin = int((skin / 3) * 1.2)
    if m_skin > 0:
        mods["damage_take"] += m_skin  # <--- ТЕПЕРЬ ПЛЮС
        logs.append(f"Кожа ({skin}): поглощает {m_skin} урона")

    # ИТОГОВЫЙ РАСЧЕТ HP/SP/STAGGER
    base_h = 20
    rolls_h = sum(5 + v.get("hp", 0) for v in unit.level_rolls.values())
    raw_h = base_h + rolls_h + hp_flat

    step1 = raw_h * (1 + hp_pct / 100.0)
    step2 = step1 * (1 + unit.implants_hp_pct / 100.0)
    final_h = step2 * (1 + unit.talents_hp_pct / 100.0)
    unit.max_hp = int(final_h)

    # SP (РАССУДОК)
    base_s = 20
    rolls_s = sum(5 + v.get("sp", 0) for v in unit.level_rolls.values())
    raw_s = base_s + rolls_s + sp_flat

    # Расчет процента
    # sp_pct - это бонус от Психики (Psych)
    # mods["max_sp_pct"] - это бонус от Талантов (Держать себя в руках)

    if mods["max_sp_pct"] > 0:
        logs.append(f"Бонус Рассудка (Таланты): +{mods['max_sp_pct']}%")

    step1_s = raw_s * (1 + sp_pct / 100.0)  # <--- Используем Total
    step2_s = step1_s * (1 + unit.implants_sp_pct / 100.0)
    final_s = step2_s * (1 + (unit.talents_sp_pct + mods["max_sp_pct"]) / 100.0)
    unit.max_sp = int(final_s)

    base_stg = unit.max_hp // 2
    final_stg = base_stg * (1 + stg_pct / 100.0)
    unit.max_stagger = int(final_stg)

    unit.current_hp = min(unit.current_hp, unit.max_hp)
    unit.current_sp = min(unit.current_sp, unit.max_sp)
    unit.current_stagger = min(unit.current_stagger, unit.max_stagger)

    unit.modifiers = mods
    return logs