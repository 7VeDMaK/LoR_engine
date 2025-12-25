import streamlit as st
import uuid
from core.models import Card, Dice, DiceType
from core.library import Library


def render_editor_page():
    st.markdown("### 🛠️ Card Creator")

    # --- 1. Основные параметры ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        name = c1.text_input("Card Name", "Vampire Strike", label_visibility="collapsed", placeholder="Card Name")
        tier = c2.selectbox("Tier", [1, 2, 3], label_visibility="collapsed")
        ctype = c3.selectbox("Type", ["melee", "ranged"], label_visibility="collapsed")

        desc = st.text_area("Description", "On Hit: Heal 2 HP", height=68,
                            placeholder="Description text...")

    # --- 2. Эффекты Карты (Card Scripts) ---
    card_scripts = {}
    with st.expander("✨ Card Effects (On Use / Passive)", expanded=False):
        ce_col1, ce_col2 = st.columns([1, 1])
        ce_trigger = ce_col1.selectbox("Trigger", ["on_use", "on_combat_end"], key="ce_trig")
        ce_type = ce_col2.selectbox("Effect", ["None", "Heal HP", "Apply Status"], key="ce_type")

        # Параметры эффекта карты
        if ce_type != "None":
            st.divider()
            script_payload = {}

            if ce_type == "Heal HP":
                amt = st.number_input("Amount", 1, 50, 5, key="ce_hp_amt")
                script_payload = {
                    "script_id": "restore_hp",
                    "params": {"amount": int(amt), "target": "self"}
                }

            elif ce_type == "Apply Status":
                c_s1, c_s2, c_s3 = st.columns([2, 1, 1])
                s_name = c_s1.selectbox("Status ID", ["strength", "endurance", "haste", "protection"], key="ce_st_name")
                s_amt = c_s2.number_input("Stack", 1, 20, 1, key="ce_st_amt")

                c_d1, c_d2 = st.columns(2)
                s_dur = c_d1.number_input("Duration", 1, 5, 1, key="ce_st_dur")
                s_del = c_d2.number_input("Delay", 0, 5, 0, key="ce_st_del")

                script_payload = {
                    "script_id": "apply_status",
                    "params": {
                        "status": s_name,
                        "stack": int(s_amt),
                        "duration": int(s_dur),
                        "delay": int(s_del),
                        "target": "self"
                    }
                }

            if script_payload:
                card_scripts[ce_trigger] = [script_payload]

    # --- 3. Кубики (Grid Layout) ---
    st.markdown("**Dice Configuration**")
    num_dice = st.slider("Dice Count", 1, 4, 1, label_visibility="collapsed")

    dice_data = []
    cols = st.columns(num_dice)

    for i in range(num_dice):
        with cols[i]:
            with st.container(border=True):
                # Заголовок кубика
                dc1, dc2 = st.columns([2, 1])
                dtype_str = dc1.selectbox("Type", ["Slash", "Pierce", "Blunt", "Block", "Evade"], key=f"d_t_{i}",
                                          label_visibility="collapsed")

                # Мин-Макс
                mm_c1, mm_c2 = st.columns(2)
                d_min = mm_c1.number_input("Min", 1, 50, 2, key=f"d_min_{i}")
                d_max = mm_c2.number_input("Max", 1, 50, 5, key=f"d_max_{i}")

                # --- POPUP с эффектами кубика ---
                with st.popover("✨ Effects", use_container_width=True):
                    st.caption(f"Dice {i + 1} Settings")

                    e1, e2 = st.columns([2, 1])
                    # === ДОБАВИЛ HEAL SELF СЮДА ===
                    eff_name = e1.selectbox("Effect",
                                            ["None", "Heal Self", "bleed", "paralysis", "burn", "strength", "weakness",
                                             "bind"], key=f"de_n_{i}")
                    eff_amt = e2.number_input("Amt", 1, 20, 1, key=f"de_a_{i}")

                    t1, t2 = st.columns(2)
                    eff_dur = t1.number_input("Dur", 1, 10, 1, key=f"de_dur_{i}")
                    eff_del = t2.number_input("Delay", 0, 10, 0, key=f"de_del_{i}")

                    eff_trig = st.selectbox("Trigger", ["on_hit", "on_clash_win", "on_clash_lose"], key=f"de_t_{i}")

                # Сборка скриптов кубика
                d_scripts = {}
                if eff_name != "None":

                    # === ЛОГИКА ДЛЯ ЛЕЧЕНИЯ ===
                    if eff_name == "Heal Self":
                        d_scripts[eff_trig] = [{
                            "script_id": "restore_hp",
                            "params": {
                                "amount": int(eff_amt),
                                "target": "self"
                            }
                        }]
                    # === ЛОГИКА ДЛЯ СТАТУСОВ ===
                    else:
                        d_scripts[eff_trig] = [{
                            "script_id": "apply_status",
                            "params": {
                                "status": eff_name,
                                "stack": int(eff_amt),
                                "duration": int(eff_dur),
                                "delay": int(eff_del),
                                "target": "target"
                            }
                        }]

                type_enum = DiceType.SLASH
                if dtype_str == "Pierce":
                    type_enum = DiceType.PIERCE
                elif dtype_str == "Blunt":
                    type_enum = DiceType.BLUNT
                elif dtype_str == "Block":
                    type_enum = DiceType.BLOCK
                elif dtype_str == "Evade":
                    type_enum = DiceType.EVADE

                dice_obj = Dice(d_min, d_max, type_enum)
                dice_obj.scripts = d_scripts
                dice_data.append(dice_obj)

    # --- 4. Сохранение ---
    st.divider()
    save_col, _ = st.columns([1, 4])
    if save_col.button("💾 Save Card", type="primary"):
        auto_id = name.lower().replace(" ", "_") + "_" + str(uuid.uuid4())[:4]
        new_card = Card(
            id=auto_id, name=name, tier=tier, card_type=ctype,
            description=desc, dice_list=dice_data, scripts=card_scripts
        )
        Library.save_card(new_card, filename="custom_cards.json")
        st.toast(f"Card '{name}' Saved!", icon="✅")