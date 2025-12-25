# ui/profile.py
import streamlit as st
from core.models import Unit, Resistances
from core.unit_library import UnitLibrary


def render_profile_page():
    st.header("👤 Character Profile")

    if 'roster' not in st.session_state or not st.session_state['roster']:
        st.warning("Roster empty. Creating new...")
        st.session_state['roster'] = {"New Unit": Unit("New Unit")}

    roster_names = list(st.session_state['roster'].keys())

    c1, c2 = st.columns([3, 1])
    selected_name = c1.selectbox("Select Character", roster_names, key="profile_selector")

    if c2.button("➕ New Unit"):
        new_name = f"Unit_{len(roster_names) + 1}"
        new_unit = Unit(name=new_name)
        st.session_state['roster'][new_name] = new_unit
        # Сразу сохраняем, чтобы файл создался
        UnitLibrary.save_unit(new_unit)
        st.rerun()

    unit = st.session_state['roster'][selected_name]

    # --- КНОПКА СОХРАНЕНИЯ ---
    col_save, col_info = st.columns([1, 5])
    with col_save:
        if st.button("💾 SAVE", type="primary"):
            if UnitLibrary.save_unit(unit):
                st.toast(f"Character '{unit.name}' saved!", icon="✅")
            else:
                st.error("Failed to save.")

    st.divider()

    # --- 2. ОБЩАЯ ИНФОРМАЦИЯ (Header) ---
    col_img, col_info = st.columns([1, 4])
    with col_img:
        st.image("https://placehold.co/150x150/png?text=Unit", caption="Avatar")

    with col_info:
        c_name, c_lvl, c_rank = st.columns([2, 1, 1])

        # Переименование - сложная штука, т.к. имя = ключ словаря и имя файла
        # Пока сделаем простое редактирование поля, но чтобы оно применилось в словарь, надо сохранить
        new_name = c_name.text_input("Name", unit.name)
        if new_name != unit.name:
            # Если имя изменилось
            old_name = unit.name
            unit.name = new_name
            # Обновляем ключ в словаре
            st.session_state['roster'][new_name] = st.session_state['roster'].pop(old_name)
            # Обновляем селектор
            st.rerun()

        unit.level = c_lvl.number_input("Level", 1, 100, unit.level)
        unit.rank = c_rank.number_input("Rank (Grade)", 1, 12, unit.rank)

    # --- 3. ЖИЗНЕННЫЕ ПОКАЗАТЕЛИ (Vitals) ---
    st.subheader("Vital Statistics")
    with st.container(border=True):
        st.markdown(f"**❤️ Health: {unit.max_hp}**")
        with st.expander("HP Details", expanded=False):
            c1, c2, c3 = st.columns(3)
            unit.base_hp = c1.number_input("Base HP", 0, 500, unit.base_hp)
            unit.max_hp = c2.number_input("Total HP (Override)", 1, 1000, unit.max_hp)
            unit.current_hp = c3.number_input("Current HP", 0, unit.max_hp, unit.current_hp)

        st.markdown(f"**🧠 Sanity (SP): {unit.max_sp}**")
        with st.expander("SP Details", expanded=False):
            c1, c2, c3 = st.columns(3)
            unit.base_sp = c1.number_input("Base SP", 0, 500, unit.base_sp)
            unit.max_sp = c2.number_input("Total SP", 1, 500, unit.max_sp)
            unit.current_sp = c3.number_input("Current SP", -45, unit.max_sp, unit.current_sp)

        c_stag, c_spd = st.columns(2)
        with c_stag:
            unit.max_stagger = st.number_input("🛡️ Stagger Threshold", 1, 200, unit.max_stagger)
            unit.current_stagger = st.number_input("Current Stagger", 0, unit.max_stagger, unit.current_stagger)
        with c_spd:
            st.write("🏃 Speed Range")
            c_min, c_max = st.columns(2)
            unit.base_speed_min = c_min.number_input("Min", 1, 20, unit.base_speed_min)
            unit.base_speed_max = c_max.number_input("Max", 1, 20, unit.base_speed_max)

    # --- 4. БРОНЯ ---
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
            r1, r2, r3 = st.columns(3)
            unit.hp_resists.slash = r1.number_input("Slash", 0.1, 2.0, unit.hp_resists.slash, 0.1)
            unit.hp_resists.pierce = r2.number_input("Pierce", 0.1, 2.0, unit.hp_resists.pierce, 0.1)
            unit.hp_resists.blunt = r3.number_input("Blunt", 0.1, 2.0, unit.hp_resists.blunt, 0.1)

    # --- 5. АТРИБУТЫ ---
    st.header("📊 Attributes")
    with st.container(border=True):
        cols = st.columns(5)
        keys = ["strength", "endurance", "agility", "wisdom", "psych"]
        for i, k in enumerate(keys):
            unit.attributes[k] = cols[i].number_input(k.capitalize(), 1, 30, unit.attributes.get(k, 1))

    # --- 6. НАВЫКИ ---
    st.header("🛠️ Skills")
    t1, t2, t3 = st.tabs(["Combat", "Weapons", "Misc"])

    with t1:
        c1, c2 = st.columns(2)
        with c1:
            unit.skills["strike_power"] = st.number_input("Strike Power", 0, 15, unit.skills.get("strike_power", 0))
            unit.skills["medicine"] = st.number_input("Medicine", 0, 30, unit.skills.get("medicine", 0))
            unit.skills["willpower"] = st.number_input("Willpower", 0, 30, unit.skills.get("willpower", 0))
            unit.skills["luck"] = st.number_input("Luck", 0, 100, unit.skills.get("luck", 0))
        with c2:
            unit.skills["acrobatics"] = st.number_input("Acrobatics", 0, 15, unit.skills.get("acrobatics", 0))
            unit.skills["shields"] = st.number_input("Shields", 0, 15, unit.skills.get("shields", 0))
            unit.skills["tough_skin"] = st.number_input("Tough Skin", 0, 15, unit.skills.get("tough_skin", 0))
            unit.skills["speed"] = st.number_input("Speed Skill", 0, 30, unit.skills.get("speed", 0))

    with t2:
        c1, c2 = st.columns(2)
        with c1:
            unit.skills["light_weapon"] = st.number_input("Light Wep", 0, 15, unit.skills.get("light_weapon", 0))
            unit.skills["medium_weapon"] = st.number_input("Medium Wep", 0, 15, unit.skills.get("medium_weapon", 0))
        with c2:
            unit.skills["heavy_weapon"] = st.number_input("Heavy Wep", 0, 15, unit.skills.get("heavy_weapon", 0))
            unit.skills["firearms"] = st.number_input("Firearms", 0, 15, unit.skills.get("firearms", 0))

    with t3:
        c1, c2 = st.columns(2)
        with c1:
            unit.skills["eloquence"] = st.number_input("Eloquence", 0, 15, unit.skills.get("eloquence", 0))
            unit.skills["forging"] = st.number_input("Forging", 0, 15, unit.skills.get("forging", 0))
        with c2:
            unit.skills["engineering"] = st.number_input("Engineering", 0, 25, unit.skills.get("engineering", 0))
            unit.skills["programming"] = st.number_input("Programming", 0, 15, unit.skills.get("programming", 0))

    # --- 7. ПАССИВКИ ---
    st.subheader("Passives & Talents")
    col_p, col_t = st.columns(2)
    with col_p:
        st.caption("Passives IDs")
        pas_str = st.text_area("CSV", ", ".join(unit.passives), key="p_edit")
        if pas_str: unit.passives = [x.strip() for x in pas_str.split(",") if x.strip()]
    with col_t:
        st.caption("Talents IDs")
        tal_str = st.text_area("CSV", ", ".join(unit.talents), key="t_edit")
        if tal_str: unit.talents = [x.strip() for x in tal_str.split(",") if x.strip()]