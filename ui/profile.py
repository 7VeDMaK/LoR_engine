import streamlit as st
from core.models import Unit, Resistances


def render_profile_page():
    st.header("👤 Character Profile")

    # --- 1. ВЫБОР ПЕРСОНАЖА (ROSTER) ---
    if 'roster' not in st.session_state:
        st.error("Roster not found!")
        return

    roster_names = list(st.session_state['roster'].keys())

    # Селектор персонажа
    c1, c2 = st.columns([3, 1])
    selected_name = c1.selectbox("Select Character", roster_names, key="profile_selector")

    # Кнопка добавления нового
    if c2.button("➕ New Unit"):
        new_name = f"New Unit {len(roster_names) + 1}"
        st.session_state['roster'][new_name] = Unit(name=new_name)
        st.rerun()

    unit = st.session_state['roster'][selected_name]

    st.divider()

    # --- 2. ОБЩАЯ ИНФОРМАЦИЯ (Header) ---
    col_img, col_info = st.columns([1, 4])

    with col_img:
        st.image("https://placehold.co/150x150/png?text=Unit", caption="Avatar")

    with col_info:
        # Редактирование имени, уровня и ранга
        c_name, c_lvl, c_rank = st.columns([2, 1, 1])

        # Переименование
        new_name = c_name.text_input("Name", unit.name)
        if new_name != unit.name:
            st.session_state['roster'][new_name] = st.session_state['roster'].pop(unit.name)
            unit.name = new_name
            st.rerun()

        unit.level = c_lvl.number_input("Level", 1, 100, unit.level)
        unit.rank = c_rank.number_input("Rank (Grade)", 1, 12, unit.rank)

        st.caption(f"Internal ID: {id(unit)}")

    # --- 3. ЖИЗНЕННЫЕ ПОКАЗАТЕЛИ (Vitals) ---
    st.subheader("Vital Statistics")

    with st.container(border=True):
        # Health Block
        st.markdown(f"**❤️ Health: {unit.max_hp}**")
        with st.expander("HP Calculation Details", expanded=False):
            c1, c2, c3 = st.columns(3)
            unit.base_hp = c1.number_input("Base HP", 0, 500, unit.base_hp)
            unit.max_hp = c2.number_input("Total HP (Override)", 1, 1000, unit.max_hp)
            unit.current_hp = c3.number_input("Current HP", 0, unit.max_hp, unit.current_hp)

        # Sanity Block
        st.markdown(f"**🧠 Sanity (SP): {unit.max_sp}**")
        with st.expander("SP Calculation Details", expanded=False):
            c1, c2, c3 = st.columns(3)
            unit.base_sp = c1.number_input("Base SP", 0, 500, unit.base_sp)
            unit.max_sp = c2.number_input("Total SP", 1, 500, unit.max_sp)
            unit.current_sp = c3.number_input("Current SP", -45, unit.max_sp, unit.current_sp)

        # Stagger & Speed
        c_stag, c_spd = st.columns(2)
        with c_stag:
            unit.max_stagger = st.number_input("🛡️ Stagger Threshold", 1, 200, unit.max_stagger)
        with c_spd:
            st.write("🏃 Speed Range")
            c_min, c_max = st.columns(2)
            unit.base_speed_min = c_min.number_input("Min", 1, 20, unit.base_speed_min, label_visibility="collapsed")
            unit.base_speed_max = c_max.number_input("Max", 1, 20, unit.base_speed_max, label_visibility="collapsed")

    # --- 4. РЕЗИСТЫ И БРОНЯ ---
    st.subheader("Defense")
    with st.container(border=True):
        c_arm, c_res = st.columns([1, 2])
        with c_arm:
            unit.armor_name = st.text_input("Armor Name", unit.armor_name)
            unit.armor_type = st.selectbox("Armor Type", ["Light", "Medium", "Heavy"],
                                           index=["Light", "Medium", "Heavy"].index(
                                               unit.armor_type) if unit.armor_type in ["Light", "Medium",
                                                                                       "Heavy"] else 1)

        with c_res:
            st.markdown("**Resistances (Slash / Pierce / Blunt)**")
            r1, r2, r3 = st.columns(3)
            unit.hp_resists.slash = r1.number_input("Slash", 0.1, 2.0, unit.hp_resists.slash, 0.1)
            unit.hp_resists.pierce = r2.number_input("Pierce", 0.1, 2.0, unit.hp_resists.pierce, 0.1)
            unit.hp_resists.blunt = r3.number_input("Blunt", 0.1, 2.0, unit.hp_resists.blunt, 0.1)

    # --- 5. ХАРАКТЕРИСТИКИ (ATTRIBUTES) ---
    st.header("📊 Attributes")
    with st.container(border=True):
        ac1, ac2, ac3, ac4, ac5 = st.columns(5)

        unit.attributes["strength"] = ac1.number_input("Strength", 1, 30, unit.attributes.get("strength", 1))
        unit.attributes["endurance"] = ac2.number_input("Endurance", 1, 30, unit.attributes.get("endurance", 1))
        unit.attributes["agility"] = ac3.number_input("Agility", 1, 30, unit.attributes.get("agility", 1))
        unit.attributes["wisdom"] = ac4.number_input("Wisdom", 1, 15, unit.attributes.get("wisdom", 1))
        unit.attributes["psych"] = ac5.number_input("Psych", 1, 30, unit.attributes.get("psych", 1))

    # --- 6. НАВЫКИ (SKILLS) ---
    st.header("🛠️ Skills")

    # Используем табы для группировки
    tab_phys, tab_wep, tab_misc = st.tabs(["Physical / Combat", "Weapon Mastery", "Tech & Social"])

    with tab_phys:
        c1, c2 = st.columns(2)
        with c1:
            unit.skills["strike_power"] = st.number_input("Strike Power (Сила удара)", 0, 15,
                                                          unit.skills.get("strike_power", 0))
            unit.skills["medicine"] = st.number_input("Medicine (Медицина)", 0, 30, unit.skills.get("medicine", 0))
            unit.skills["willpower"] = st.number_input("Willpower (Сила воли)", 0, 30, unit.skills.get("willpower", 0))
            unit.skills["luck"] = st.number_input("Luck (Удача)", 0, 100, unit.skills.get("luck", 0))
        with c2:
            unit.skills["acrobatics"] = st.number_input("Acrobatics (Акробатика)", 0, 15,
                                                        unit.skills.get("acrobatics", 0))
            unit.skills["shields"] = st.number_input("Shields (Щиты)", 0, 15, unit.skills.get("shields", 0))
            unit.skills["tough_skin"] = st.number_input("Tough Skin (Крепкая кожа)", 0, 15,
                                                        unit.skills.get("tough_skin", 0))
            unit.skills["speed"] = st.number_input("Speed Skill (Скорость)", 0, 30, unit.skills.get("speed", 0))

    with tab_wep:
        c1, c2 = st.columns(2)
        with c1:
            unit.skills["light_weapon"] = st.number_input("Light Weapon (Легкое)", 0, 15,
                                                          unit.skills.get("light_weapon", 0))
            unit.skills["medium_weapon"] = st.number_input("Medium Weapon (Среднее)", 0, 15,
                                                           unit.skills.get("medium_weapon", 0))
        with c2:
            unit.skills["heavy_weapon"] = st.number_input("Heavy Weapon (Тяжелое)", 0, 15,
                                                          unit.skills.get("heavy_weapon", 0))
            unit.skills["firearms"] = st.number_input("Firearms (Огнестрел)", 0, 15, unit.skills.get("firearms", 0))

    with tab_misc:
        c1, c2 = st.columns(2)
        with c1:
            unit.skills["eloquence"] = st.number_input("Eloquence (Красноречие)", 0, 15,
                                                       unit.skills.get("eloquence", 0))
            unit.skills["forging"] = st.number_input("Forging (Ковка)", 0, 15, unit.skills.get("forging", 0))
        with c2:
            unit.skills["engineering"] = st.number_input("Engineering (Инженерия)", 0, 25,
                                                         unit.skills.get("engineering", 0))
            unit.skills["programming"] = st.number_input("Programming (Программирование)", 0, 15,
                                                         unit.skills.get("programming", 0))

    # --- 7. ТАЛАНТЫ И ПАССИВКИ ---
    st.subheader("Talents & Passives")

    col_p, col_t = st.columns(2)

    with col_p:
        st.caption("Passives")
        # Отображение списка как строки
        st.text_area("Passive IDs (comma separated)",
                     value=", ".join(unit.passives),
                     key="passives_edit_area",
                     help="Enter IDs like: Lone Fixer, Strength")
        # Обновление списка из текста
        new_passives_str = st.session_state.get("passives_edit_area", "")
        if new_passives_str:
            # Очистка и разделение
            cleaned = [p.strip() for p in new_passives_str.split(",") if p.strip()]
            unit.passives = cleaned

    with col_t:
        st.caption("Talents")
        st.text_area("Talents (comma separated)",
                     value=", ".join(unit.talents),
                     key="talents_edit_area")
        new_talents_str = st.session_state.get("talents_edit_area", "")
        if new_talents_str:
            cleaned_t = [t.strip() for t in new_talents_str.split(",") if t.strip()]
            unit.talents = cleaned_t