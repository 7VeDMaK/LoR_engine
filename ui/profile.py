import streamlit as st
import random
import os
from core.models import Unit
from core.unit_library import UnitLibrary

ATTR_LABELS = {"strength": "Сила", "endurance": "Стойкость", "agility": "Ловкость", "wisdom": "Мудрость",
               "psych": "Психика"}
SKILL_LABELS = {
    "strike_power": "Сила удара", "medicine": "Медицина", "willpower": "Сила воли", "luck": "Удача",
    "acrobatics": "Акробатика", "shields": "Щиты", "tough_skin": "Крепкая кожа", "speed": "Скорость",
    "light_weapon": "Лёгкое оружие", "medium_weapon": "Среднее оружие", "heavy_weapon": "Тяжёлое оружие",
    "firearms": "Огнестрел",
    "eloquence": "Красноречие", "forging": "Ковка", "engineering": "Инженерия", "programming": "Программирование"
}


def save_avatar_file(uploaded, unit_name):
    os.makedirs("data/avatars", exist_ok=True)
    safe = "".join(c for c in unit_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(" ", "_")
    path = f"data/avatars/{safe}.{uploaded.name.split('.')[-1]}"
    with open(path, "wb") as f: f.write(uploaded.getbuffer())
    return path


def render_profile_page():
    if 'roster' not in st.session_state or not st.session_state['roster']:
        st.session_state['roster'] = UnitLibrary.load_all() or {"New Unit": Unit("New Unit")}

    roster = st.session_state['roster']
    c1, c2 = st.columns([3, 1])
    sel = c1.selectbox("Персонаж", list(roster.keys()))
    if c2.button("➕"):
        n = f"Unit_{len(roster) + 1}";
        u = Unit(n);
        roster[n] = u;
        UnitLibrary.save_unit(u);
        st.rerun()

    unit = roster[sel]

    if st.button("💾 СОХРАНИТЬ", type="primary", use_container_width=True):
        UnitLibrary.save_unit(unit);
        st.toast("Сохранено!", icon="✅")

    st.divider()

    col_l, col_r = st.columns([1, 3], gap="small")

    # --- ЛЕВАЯ КОЛОНКА ---
    with col_l:
        img = unit.avatar if unit.avatar and os.path.exists(unit.avatar) else "https://placehold.co/150x150/png?text=?"
        st.image(img, use_container_width=True)
        upl = st.file_uploader("Арт", type=['png', 'jpg'], label_visibility="collapsed")
        if upl: unit.avatar = save_avatar_file(upl, unit.name); UnitLibrary.save_unit(unit); st.rerun()

        unit.name = st.text_input("Имя", unit.name)
        c_l, c_r = st.columns(2)
        unit.level = c_l.number_input("Ур.", 1, 90, unit.level)
        unit.rank = c_r.number_input("Ранг", 1, 12, unit.rank)

        st.caption("Базовый Интеллект")
        unit.base_intellect = st.number_input("Int Base", 1, 30, unit.base_intellect, label_visibility="collapsed")
        st.info(f"Интеллект: **{unit.base_intellect + (unit.attributes['wisdom'] // 3)}**")

        st.divider()
        st.markdown(f"**🧊 Скорость:**")
        # Отображаем индивидуально рассчитанные кубики
        if unit.computed_speed_dice:
            for d in unit.computed_speed_dice:
                st.markdown(f"🧊 {d[0]}~{d[1]}")
        else:
            # Фолбек для 0 уровня
            st.markdown(f"🧊 {unit.speed_min}~{unit.speed_max}")

    # --- ПРАВАЯ КОЛОНКА ---
    with col_r:
        # ИМПЛАНТЫ И РЕЗИСТЫ
        with st.expander("⚙️ Импланты, Резисты и Броня", expanded=False):
            c1, c2 = st.columns(2)
            c1.markdown("**Импланты и Таланты (%)**")
            pc1, pc2 = c1.columns(2)
            unit.implants_hp_pct = pc1.number_input("HP Импл %", 0, 200, unit.implants_hp_pct)
            unit.implants_sp_pct = pc2.number_input("SP Импл %", 0, 200, unit.implants_sp_pct)
            unit.talents_hp_pct = pc1.number_input("HP Талант %", 0, 200, unit.talents_hp_pct)
            unit.talents_sp_pct = pc2.number_input("SP Талант %", 0, 200, unit.talents_sp_pct)

            c2.markdown("**Броня и Резисты**")
            unit.armor_name = c2.text_input("Название Брони", unit.armor_name)
            r1, r2, r3 = c2.columns(3)
            unit.hp_resists.slash = r1.number_input("Slash", 0.1, 2.0, unit.hp_resists.slash)
            unit.hp_resists.pierce = r2.number_input("Pierce", 0.1, 2.0, unit.hp_resists.pierce)
            unit.hp_resists.blunt = r3.number_input("Blunt", 0.1, 2.0, unit.hp_resists.blunt)

        # ТЕКУЩИЕ СТАТЫ
        with st.container(border=True):
            sc1, sc2, sc3 = st.columns(3)
            sc1.markdown(f"**HP** (Max {unit.max_hp})");
            unit.current_hp = sc1.number_input("hp", 0, 9999, unit.current_hp, label_visibility="collapsed")
            sc2.markdown(f"**SP** (Max {unit.max_sp})");
            unit.current_sp = sc2.number_input("sp", -45, 9999, unit.current_sp, label_visibility="collapsed")
            sc3.markdown(f"**Stagger** (Max {unit.max_stagger})");
            unit.current_stagger = sc3.number_input("stg", 0, 9999, unit.current_stagger, label_visibility="collapsed")

        # ОЧКИ И БРОСКИ
        with st.container(border=True):
            lvl_growth = max(0, unit.level - 1)
            total_attr = 25 + lvl_growth
            total_skill = 38 + (lvl_growth * 2)
            total_tal = unit.level // 3

            spent_a = sum(unit.attributes.values())
            spent_s = sum(unit.skills.values())
            spent_t = len(unit.talents)

            c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
            c1.metric("Хар-ки", total_attr - spent_a)
            c2.metric("Навыки", total_skill - spent_s)
            c3.metric("Таланты", total_tal - spent_t)

            with st.expander("🎲 История Бросков HP/SP"):
                missing = [i for i in range(3, unit.level + 1, 3) if str(i) not in unit.level_rolls]
                if missing:
                    if st.button("Бросить кубики"):
                        for l in missing: unit.level_rolls[str(l)] = {"hp": random.randint(1, 5),
                                                                      "sp": random.randint(1, 5)}
                        UnitLibrary.save_unit(unit);
                        st.rerun()

                if unit.level_rolls:
                    for lvl in sorted(map(int, unit.level_rolls.keys())):
                        r = unit.level_rolls[str(lvl)]
                        st.caption(f"Lvl {lvl}: +{5 + r['hp']} HP, +{5 + r['sp']} SP (d5: {r['hp']}, {r['sp']})")
                else:
                    st.caption("Нет записей о бросках.")

        st.caption("Характеристики")
        acols = st.columns(5)
        for i, k in enumerate(["strength", "endurance", "agility", "wisdom", "psych"]):
            unit.attributes[k] = acols[i].number_input(ATTR_LABELS[k], 0, 30, unit.attributes[k])

        st.caption("Навыки")
        with st.expander("Список навыков", expanded=True):
            scols = st.columns(3)
            for i, k in enumerate(SKILL_LABELS.keys()):
                unit.skills[k] = scols[i % 3].number_input(SKILL_LABELS[k], 0, 30, unit.skills[k])

    logs = unit.recalculate_stats()

    st.markdown("---")
    with st.expander("📜 Подробный лог бонусов", expanded=False):
        if logs:
            for l in logs:
                color = "gray"
                if "урона" in l or "атаки" in l or "удара" in l:
                    color = "red"
                elif "здоровья" in l or "блока" in l or "щита" in l:
                    color = "blue"
                elif "рассудка" in l:
                    color = "orange"
                elif "инициативу" in l or "уклонения" in l or "кость" in l:
                    color = "green"
                elif "интеллекта" in l:
                    color = "violet"

                st.markdown(f":{color}[• {l}]")
        else:
            st.caption("Нет активных бонусов.")

    with st.expander("Дополнительно (Пассивки)"):
        unit.passives = [x.strip() for x in st.text_area("ID Пассивок", ", ".join(unit.passives)).split(",") if
                         x.strip()]