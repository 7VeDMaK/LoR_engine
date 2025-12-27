import math
from logic.passives import PASSIVE_REGISTRY
from logic.talents import TALENT_REGISTRY

# Эмодзи
I_ATK, I_HP, I_BLK = "⬆", "🤎", "🛡️"
I_INIT, I_EVD, I_SP, I_DICE = "👢", "🌀", "🧠", "🧊"


def recalculate_unit_stats(unit):
    logs = []

    # 1. Инициализация модификаторов
    mods = {
        "power_all": 0, "power_attack": 0, "power_block": 0, "power_evade": 0,
        "damage_deal": 0, "damage_take": 0, "heal_efficiency": 0.0, "initiative": 0,
        "power_light": 0, "power_medium": 0, "power_heavy": 0, "power_ranged": 0,
        # Сюда мы запишем итоговые значения, чтобы UI их видел
        "total_intellect": 0
    }

    # 2. Сбор бонусов от способностей
    # Собираем список всех ключей, которые могут быть усилены (Атрибуты + Навыки)
    all_stat_keys = list(unit.attributes.keys()) + list(unit.skills.keys())
    # Добавляем спец. ключи
    all_stat_keys.append("bonus_intellect")

    bonuses = {k: 0 for k in all_stat_keys}

    # Собираем активные эффекты
    abilities = []
    for pid in unit.passives:
        if pid in PASSIVE_REGISTRY: abilities.append(PASSIVE_REGISTRY[pid])
    for pid in unit.talents:
        if pid in TALENT_REGISTRY: abilities.append(TALENT_REGISTRY[pid])

    # Суммируем бонусы
    for ab in abilities:
        ab_bonuses = ab.on_calculate_stats(unit)
        for stat, val in ab_bonuses.items():
            if stat in bonuses:
                bonuses[stat] += val
            else:
                # Нестандартные моды (backstab и т.д.) сразу в mods
                if stat not in mods: mods[stat] = 0
                mods[stat] += val

    # === 3. РАСЧЕТ ИТОГОВЫХ ЗНАЧЕНИЙ ===

    # Helper: считает Total, пишет в mods, возвращает значение
    def get_total(container, key):
        base = container.get(key, 0)
        bonus = bonuses.get(key, 0)
        total = base + bonus
        mods[f"total_{key}"] = total  # Сохраняем для UI (например total_strength, total_luck)
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

    # НАВЫКИ (SKILLS)
    # Мы проходимся по всем навыкам и считаем их Total
    # Теперь в формулах ниже мы будем брать значения из этих переменных
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

    # === 4. ПРИМЕНЕНИЕ ЭФФЕКТОВ (ЛОГИКА) ===

    # --- Strength ---
    if (strength // 3) > 0: logs.append(f"Сила ({strength}): +{strength // 3} к проверкам")
    if (strength // 5) > 0:
        mods["power_attack"] += strength // 5
        logs.append(f"Сила ({strength}): +{strength // 5} {I_ATK} Power")

    # --- Endurance ---
    hp_flat = (endurance // 3) * 5
    hp_pct = min(endurance * 2, 100)
    if hp_pct > 0: logs.append(f"Стойкость ({endurance}): HP +{hp_pct}%")
    if hp_flat > 0: logs.append(f"Стойкость ({endurance}): HP +{hp_flat}")
    if (endurance // 5) > 0:
        mods["power_block"] += endurance // 5
        logs.append(f"Стойкость ({endurance}): +{endurance // 5} {I_BLK} Power")

    # --- Agility ---
    if (agility // 3) > 0:
        mods["initiative"] += agility // 3
        logs.append(f"Ловкость ({agility}): Инициатива +{agility // 3}")
    if (agility // 5) > 0:
        mods["power_evade"] += agility // 5
        logs.append(f"Ловкость ({agility}): +{agility // 5} {I_EVD} Power")

    # --- Wisdom & Intellect ---
    if (wisdom // 3) > 0: logs.append(f"Мудрость ({wisdom}): +{wisdom // 3} к Интеллекту")
    if bonuses["bonus_intellect"] > 0: logs.append(f"Бонус Интеллекта: +{bonuses['bonus_intellect']}")

    # --- Psych ---
    sp_flat = (psych // 3) * 5
    sp_pct = min(psych * 2, 100)
    if sp_pct > 0: logs.append(f"Психика ({psych}): SP +{sp_pct}%")
    if sp_flat > 0: logs.append(f"Психика ({psych}): SP +{sp_flat}")

    # --- Skills Effects ---

    if (strike // 3) > 0:
        mods["damage_deal"] += strike // 3
        logs.append(f"Сила удара ({strike}): +{strike // 3} dmg")

    if (med // 3) > 0:
        eff = med * 10
        mods["heal_efficiency"] += eff / 100.0
        logs.append(f"Медицина ({med}): +{eff}% heal")

    stg_pct = min(will, 50)
    if stg_pct > 0: logs.append(f"Воля ({will}): Stagger +{stg_pct}%")

    if luck > 0: logs.append(f"Удача ({luck}): Повышает шанс удачных событий")

    mod_acro = int((acro / 3) * 0.8)
    if mod_acro > 0:
        mods["power_evade"] += mod_acro
        logs.append(f"Акробатика ({acro}): +{mod_acro} Evade")

    mod_shields = math.ceil((shields / 3) * 0.8) if shields >= 3 else 0
    if mod_shields > 0:
        mods["power_block"] += mod_shields
        logs.append(f"Щиты ({shields}): +{mod_shields} Block")

    # Оружие
    if (w_light // 3) > 0: mods["power_light"] += w_light // 3
    if (w_med // 3) > 0: mods["power_medium"] += w_med // 3
    if (w_heavy // 3) > 0: mods["power_heavy"] += w_heavy // 3
    if (w_fire // 3) > 0: mods["power_ranged"] += w_fire // 3

    # Скорость (Speed) - СЛОЖНАЯ ЛОГИКА
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
            # Для каждого кубика берем уровень навыка (Total)
            points = max(0, min(10, spd - (i * 10)))
            skill_bonus = points // 2

        d_min = unit.base_speed_min + global_init + skill_bonus
        d_max = unit.base_speed_max + global_init + skill_bonus
        final_dice.append((d_min, d_max))

    unit.computed_speed_dice = final_dice
    unit.speed_dice_count = dice_count
    if (spd // 10) > 0: logs.append(f"Скорость ({spd}): {dice_count} слота")

    # Кожа
    m_skin = int((skin / 3) * 1.2)
    if m_skin > 0:
        mods["damage_take"] -= m_skin
        logs.append(f"Кожа ({skin}): -{m_skin} dmg take")

    # Социальные (просто лог)
    if elo > 0: logs.append(f"Красноречие: {elo}")
    if forg > 0: logs.append(f"Ковка: {forg}")
    if eng > 0: logs.append(f"Инженерия: {eng}")
    if prog > 0: logs.append(f"Программирование: {prog}")

    # === 5. ИТОГОВЫЙ РАСЧЕТ HP/SP/STAGGER ===
    base_h = 20
    rolls_h = sum(5 + v.get("hp", 0) for v in unit.level_rolls.values())
    raw_h = base_h + rolls_h + hp_flat

    step1 = raw_h * (1 + hp_pct / 100.0)
    step2 = step1 * (1 + unit.implants_hp_pct / 100.0)
    final_h = step2 * (1 + unit.talents_hp_pct / 100.0)
    unit.max_hp = int(final_h)

    base_s = 20
    rolls_s = sum(5 + v.get("sp", 0) for v in unit.level_rolls.values())
    raw_s = base_s + rolls_s + sp_flat

    step1_s = raw_s * (1 + sp_pct / 100.0)
    step2_s = step1_s * (1 + unit.implants_sp_pct / 100.0)
    final_s = step2_s * (1 + unit.talents_sp_pct / 100.0)
    unit.max_sp = int(final_s)

    base_stg = unit.max_hp // 2
    final_stg = base_stg * (1 + stg_pct / 100.0)
    unit.max_stagger = int(final_stg)

    unit.current_hp = min(unit.current_hp, unit.max_hp)
    unit.current_sp = min(unit.current_sp, unit.max_sp)
    unit.current_stagger = min(unit.current_stagger, unit.max_stagger)

    unit.modifiers = mods
    return logs