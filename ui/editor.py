import streamlit as st
import uuid
from core.models import Card, Dice, DiceType
from core.library import Library


def render_editor_page():
    st.markdown("### 🛠️ Card Creator")

    # --- 1. Основные параметры (Компактно) ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        name = c1.text_input("Name", "Слежка", label_visibility="collapsed", placeholder="Card Name")
        tier = c2.selectbox("Tier", [1, 2, 3], label_visibility="collapsed")
        ctype = c3.selectbox("Type", ["melee", "ranged"], label_visibility="collapsed")

        desc = st.text_area("Description", "При Использовании: восстанавливает 1 HP", height=68,
                            placeholder="Description text...")

    # --- 2. Эффекты Карты (Card Scripts) ---
    # Здесь мы добавляем эффект "On Use -> Heal"
    card_scripts = {}
    with st.expander("✨ Card Effects (On Use / Passive)", expanded=False):
        ce_col1, ce_col2, ce_col3 = st.columns([1, 1, 1])
        ce_trigger = ce_col1.selectbox("Trigger", ["on_use", "on_combat_end"], key="ce_trig")
        ce_type = ce_col2.selectbox("Effect", ["None", "Heal HP", "Apply Status"], key="ce_type")

        ce_val = 0
        ce_stat = ""

        if ce_type == "Heal HP":
            ce_val = ce_col3.number_input("Amount", 1, 20, 1, key="ce_val_hp")
            if ce_type != "None":
                card_scripts[ce_trigger] = [{
                    "script_id": "restore_hp",
                    "params": {"amount": int(ce_val), "target": "self"}
                }]
        elif ce_type == "Apply Status":
            # Упрощенно для примера
            ce_stat = ce_col3.text_input("Status ID", "strength", key="ce_stat_id")

    # --- 3. Кубики (Grid Layout) ---
    st.markdown("**Dice Configuration**")
    num_dice = st.slider("Dice Count", 1, 4, 1, label_visibility="collapsed")

    dice_data = []

    # Используем колонки для отображения кубиков в ряд
    cols = st.columns(num_dice)

    for i in range(num_dice):
        with cols[i]:
            with st.container(border=True):
                # Заголовок кубика
                dc1, dc2 = st.columns([2, 1])
                dtype_str = dc1.selectbox("Type", ["Slash", "Pierce", "Blunt", "Block", "Evade"], key=f"d_t_{i}",
                                          label_visibility="collapsed")

                # Мин-Макс в одну строку
                mm_c1, mm_c2 = st.columns(2)
                d_min = mm_c1.number_input("Min", 1, 50, 1, key=f"d_min_{i}")
                d_max = mm_c2.number_input("Max", 1, 50, 4, key=f"d_max_{i}")

                # Скрипты кубика (спрятаны в toggle/expander, чтобы не занимать место)
                with st.popover("Effects"):
                    eff_name = st.selectbox("Status", ["None", "bleed", "paralysis", "burn"], key=f"de_n_{i}")
                    eff_amt = st.number_input("Amt", 1, 10, 1, key=f"de_a_{i}")
                    eff_trig = st.selectbox("When", ["on_hit", "on_clash_win"], key=f"de_t_{i}")

                # Сборка скриптов кубика
                d_scripts = {}
                if eff_name != "None":
                    d_scripts[eff_trig] = [{
                        "script_id": "apply_status",
                        "params": {"status": eff_name, "stack": int(eff_amt), "target": "target"}
                    }]

                # Конвертация типа
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