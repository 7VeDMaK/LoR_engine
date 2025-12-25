import streamlit as st
import uuid
from core.models import Card, Dice, DiceType
from core.library import Library


def render_editor_page():
    st.header("🛠️ Card Creator (Status Update)")
    st.info("Создайте карту и добавьте эффекты (Кровотечение, Паралич и т.д.)")

    st.subheader("Настройка Кубиков")
    num_dice = st.slider("Количество кубиков", 1, 4, 3)

    with st.form("new_card_form"):
        c1, c2 = st.columns([3, 1])
        name = c1.text_input("Название карты", "Frenzy")
        tier = c2.selectbox("Уровень (Tier)", [1, 2, 3], index=0)

        c3, c4 = st.columns(2)
        ctype = c3.selectbox("Тип", ["melee", "ranged"])
        desc = c4.text_area("Описание", "On Hit: Inflict 1 Bleed")

        st.divider()

        dice_data = []
        available_statuses = ["None", "bleed", "paralysis", "burn", "strength", "weakness", "haste", "bind"]

        for i in range(num_dice):
            with st.container(border=True):
                st.markdown(f"**🎲 Кубик {i + 1}**")

                dc1, dc2, dc3, dc4 = st.columns([1.5, 1, 1, 2])
                d_type_str = dc1.selectbox(f"Тип", ["Slash", "Pierce", "Blunt", "Block", "Evade"], key=f"d_type_{i}")
                d_min = dc2.number_input(f"Min", 1, 50, 2, key=f"d_min_{i}")
                d_max = dc3.number_input(f"Max", 1, 50, 4, key=f"d_max_{i}")

                st.markdown("👇 **Эффект (Script)**")
                ec1, ec2, ec3 = st.columns([2, 1, 1.5])

                effect_name = ec1.selectbox("Наложить статус", available_statuses, key=f"eff_name_{i}")
                effect_amt = ec2.number_input("Сила", 1, 10, 1, key=f"eff_amt_{i}")
                trigger = ec3.selectbox("Триггер", ["on_hit", "on_clash_win", "on_use"], key=f"trig_{i}")

                scripts_dict = {}
                if effect_name != "None":
                    script_payload = {
                        "script_id": "apply_status",
                        "params": {"status": effect_name, "stack": int(effect_amt), "target": "target"}
                    }
                    scripts_dict[trigger] = [script_payload]

                type_enum = DiceType.SLASH
                if d_type_str == "Pierce":
                    type_enum = DiceType.PIERCE
                elif d_type_str == "Blunt":
                    type_enum = DiceType.BLUNT
                elif d_type_str == "Block":
                    type_enum = DiceType.BLOCK
                elif d_type_str == "Evade":
                    type_enum = DiceType.EVADE

                dice_obj = Dice(d_min, d_max, type_enum)
                dice_obj.scripts = scripts_dict
                dice_data.append(dice_obj)

        st.divider()
        auto_id = name.lower().replace(" ", "_") + "_" + str(uuid.uuid4())[:4]
        card_id = st.text_input("Unique ID", auto_id)

        submitted = st.form_submit_button("💾 Сохранить в Библиотеку", type="primary")

        if submitted:
            new_card = Card(
                id=card_id, name=name, tier=tier, card_type=ctype,
                description=desc, dice_list=dice_data
            )
            Library.save_card(new_card, filename="custom_cards.json")
            st.success(f"Карта '{name}' ({len(dice_data)} кубиков) сохранена!")
            st.balloons()