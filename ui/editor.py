# ui/editor.py
import streamlit as st
import uuid
from core.models import Card, Dice, DiceType
from core.library import Library
from logic.status_definitions import STATUS_REGISTRY


def render_editor_page():
    st.markdown("### 🛠️ Card Creator & Editor")

    # === 0. ЗАГРУЗКА СУЩЕСТВУЮЩИХ КАРТ ===
    all_cards = Library.get_all_cards()
    # Сортируем для удобства
    all_cards.sort(key=lambda x: x.name)

    # Создаем словарь { "Имя карты (ID)": card_obj }
    card_options = {"(Создать новую)": None}
    for c in all_cards:
        key = f"{c.name} ({c.id[:4]}..)"
        card_options[key] = c

    st.info("Выберите карту из списка и нажмите 'Загрузить', чтобы отредактировать её.")

    c_load_sel, c_load_btn = st.columns([3, 1])
    selected_option = c_load_sel.selectbox("Шаблон карты", list(card_options.keys()), label_visibility="collapsed")

    # Кнопка загрузки
    if c_load_btn.button("📥 Загрузить", type="secondary", use_container_width=True):
        card = card_options[selected_option]
        if card is None:
            # Сброс (Новая карта)
            st.session_state["ed_name"] = "New Card"
            st.session_state["ed_desc"] = ""
            st.session_state["ed_tier"] = 1
            st.session_state["ed_type"] = "melee"
            st.session_state["ed_num_dice"] = 1
            # Сбрасываем ID, чтобы создалась новая
            if "ed_loaded_id" in st.session_state: del st.session_state["ed_loaded_id"]
        else:
            # Заполняем поля из карты
            st.session_state["ed_name"] = card.name
            st.session_state["ed_desc"] = card.description
            st.session_state["ed_tier"] = card.tier
            st.session_state["ed_type"] = card.card_type
            st.session_state["ed_num_dice"] = len(card.dice_list)
            # Запоминаем ID, чтобы при сохранении можно было перезаписать (если нужно)
            st.session_state["ed_loaded_id"] = card.id

            # --- ЗАГРУЗКА СКРИПТОВ КАРТЫ (On Use) ---
            # Пытаемся восстановить настройки UI по первому скрипту в on_use (упрощенно)
            # Сбрасываем значения
            st.session_state["ce_type"] = "None"

            if "on_use" in card.scripts and card.scripts["on_use"]:
                script = card.scripts["on_use"][0]
                sid = script.get("script_id")
                p = script.get("params", {})

                if sid == "restore_hp":
                    st.session_state["ce_type"] = "Restore HP"
                    st.session_state["ce_hp_amt"] = p.get("amount", 5)
                elif sid == "apply_status":
                    st.session_state["ce_type"] = "Apply Status"
                    st.session_state["ce_st_name"] = p.get("status", "bleed")
                    st.session_state["ce_st_amt"] = p.get("stack", 1)
                    st.session_state["ce_st_dur"] = p.get("duration", 1)
                    st.session_state["ce_st_del"] = p.get("delay", 0)
                    st.session_state["ce_st_tgt"] = p.get("target", "target")
                elif sid == "steal_status":
                    st.session_state["ce_type"] = "Steal Status"
                    st.session_state["ce_steal_st"] = p.get("status", "smoke")

            # --- ЗАГРУЗКА КУБИКОВ ---
            for i, d in enumerate(card.dice_list):
                # Базовые статы кубика
                st.session_state[f"d_t_{i}"] = d.dtype.value  # Slash/Pierce...
                st.session_state[f"d_min_{i}"] = d.min_val
                st.session_state[f"d_max_{i}"] = d.max_val

                # Скрипты кубика (пытаемся найти первый попавшийся триггер)
                st.session_state[f"de_type_{i}"] = "None"  # Сброс

                found_script = None
                found_trigger = "on_hit"

                for trig in ["on_hit", "on_clash_win", "on_clash_lose"]:
                    if trig in d.scripts and d.scripts[trig]:
                        found_script = d.scripts[trig][0]
                        found_trigger = trig
                        break

                if found_script:
                    st.session_state[f"de_trig_{i}"] = found_trigger
                    sid = found_script.get("script_id")
                    p = found_script.get("params", {})

                    if sid == "restore_hp":
                        st.session_state[f"de_type_{i}"] = "Restore HP"
                        st.session_state[f"de_h_amt_{i}"] = p.get("amount", 2)
                    elif sid == "apply_status":
                        st.session_state[f"de_type_{i}"] = "Apply Status"
                        st.session_state[f"de_s_name_{i}"] = p.get("status", "bleed")
                        st.session_state[f"de_s_amt_{i}"] = p.get("stack", 1)
                        st.session_state[f"de_tgt_{i}"] = p.get("target", "target")
                        st.session_state[f"de_min_roll_{i}"] = p.get("min_roll", 0)
                    elif sid == "steal_status":
                        st.session_state[f"de_type_{i}"] = "Steal Status"
                        st.session_state[f"de_steal_{i}"] = p.get("status", "smoke")
                        st.session_state[f"de_min_roll_steal_{i}"] = p.get("min_roll", 0)
                    elif sid == "multiply_status":
                        st.session_state[f"de_type_{i}"] = "Multiply Status"
                        st.session_state[f"de_mul_n_{i}"] = p.get("status", "smoke")
                        st.session_state[f"de_mul_v_{i}"] = p.get("multiplier", 2.0)
                        st.session_state[f"de_mul_t_{i}"] = p.get("target", "target")
                    elif sid == "deal_custom_damage":
                        st.session_state[f"de_type_{i}"] = "Custom Damage"
                        st.session_state[f"de_cd_t_{i}"] = p.get("type", "stagger")
                        st.session_state[f"de_cd_s_{i}"] = p.get("scale", 1.0)
                        st.session_state[f"de_cd_tg_{i}"] = p.get("target", "target")
                        st.session_state[f"de_cd_p_{i}"] = p.get("prevent_standard", False)

    # === 1. ОСНОВНЫЕ ПАРАМЕТРЫ ===
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        # Важно: используем key, чтобы управлять значениями через session_state
        name = c1.text_input("Card Name", key="ed_name", value="New Card")
        tier = c2.selectbox("Tier", [1, 2, 3], key="ed_tier")
        ctype = c3.selectbox("Type", ["melee", "ranged"], key="ed_type")

        desc = st.text_area("Description", key="ed_desc", height=68)

    # === 2. ЭФФЕКТЫ КАРТЫ (On Use) ===
    available_statuses = sorted(list(STATUS_REGISTRY.keys()))
    card_scripts = {}

    with st.expander("✨ Эффекты карты (On Use)", expanded=False):
        ce_col1, ce_col2, ce_col3 = st.columns([1, 1, 1])
        ce_trigger = ce_col1.selectbox("Триггер", ["on_use", "on_combat_end"], key="ce_trig")
        ce_type = ce_col2.selectbox("Тип эффекта", ["None", "Restore HP", "Apply Status", "Steal Status"],
                                    key="ce_type")

        script_payload = {}

        if ce_type == "Restore HP":
            amt = ce_col3.number_input("HP Amount", 1, 100, 5, key="ce_hp_amt")
            script_payload = {
                "script_id": "restore_hp",
                "params": {"amount": int(amt), "target": "self"}
            }

        elif ce_type == "Apply Status":
            with st.container(border=True):
                cs1, cs2 = st.columns(2)
                s_name = cs1.selectbox("Выберите статус", available_statuses, key="ce_st_name")
                s_amt = cs2.number_input("Кол-во (Stacks)", 1, 50, 2, key="ce_st_amt")

                cd1, cd2, cd3 = st.columns(3)
                s_dur = cd1.number_input("Длительность", 1, 10, 1, key="ce_st_dur")
                s_del = cd2.number_input("Задержка", 0, 5, 0, key="ce_st_del")
                s_tgt = cd3.selectbox("Цель", ["self", "target", "all"], key="ce_st_tgt",
                                      format_func=lambda x: "Self + Target" if x == "all" else x.capitalize())

                script_payload = {
                    "script_id": "apply_status",
                    "params": {
                        "status": s_name, "stack": int(s_amt), "duration": int(s_dur),
                        "delay": int(s_del), "target": s_tgt
                    }
                }

        elif ce_type == "Steal Status":
            st_name = ce_col3.selectbox("Status to Steal", ["smoke", "strength", "charge"], key="ce_steal_st")
            script_payload = {
                "script_id": "steal_status",
                "params": {"status": st_name}
            }

        if script_payload:
            card_scripts[ce_trigger] = [script_payload]

    # === 3. КУБИКИ (DICE) ===
    st.divider()
    st.markdown("**Настройка кубиков**")

    # Используем session_state для количества, чтобы оно обновлялось при загрузке
    if "ed_num_dice" not in st.session_state: st.session_state["ed_num_dice"] = 2
    num_dice = st.number_input("Количество кубиков", 1, 5, key="ed_num_dice")

    dice_data = []
    tabs = st.tabs([f"Dice {i + 1}" for i in range(num_dice)])

    for i, tab in enumerate(tabs):
        with tab:
            d_col1, d_col2, d_col3 = st.columns([1, 1, 1])

            dtype_str = d_col1.selectbox("Тип", ["Slash", "Pierce", "Blunt", "Block", "Evade"], key=f"d_t_{i}")
            d_min = d_col2.number_input("Min", 1, 50, 3, key=f"d_min_{i}")
            d_max = d_col3.number_input("Max", 1, 50, 7, key=f"d_max_{i}")

            st.caption("Эффект (Script)")
            de_type = st.selectbox("Эффект кубика",
                                   ["None", "Apply Status", "Restore HP", "Steal Status", "Multiply Status",
                                    "Custom Damage"], key=f"de_type_{i}")

            d_scripts = {}
            dice_payload = {}
            d_min_roll = 0

            if de_type != "None":
                de_trig = st.selectbox("Условие", ["on_hit", "on_clash_win", "on_clash_lose"], key=f"de_trig_{i}")

                if de_type == "Restore HP":
                    damt = st.number_input("Heal Amount", 1, 20, 2, key=f"de_h_amt_{i}")
                    dice_payload = {"script_id": "restore_hp", "params": {"amount": int(damt), "target": "self"}}

                elif de_type == "Apply Status":
                    ds1, ds2 = st.columns(2)
                    d_s_name = ds1.selectbox("Статус", available_statuses, key=f"de_s_name_{i}")
                    d_s_amt = ds2.number_input("Stack", 1, 20, 1, key=f"de_s_amt_{i}")
                    d_min_roll = st.number_input("Мин. бросок", 0, 50, 0, key=f"de_min_roll_{i}")
                    d_tgt = st.radio("Цель", ["target", "self"], horizontal=True, key=f"de_tgt_{i}")

                    dice_payload = {
                        "script_id": "apply_status",
                        "params": {"status": d_s_name, "stack": int(d_s_amt), "target": d_tgt}
                    }

                elif de_type == "Steal Status":
                    st_steal = st.selectbox("Status", ["smoke", "strength"], key=f"de_steal_{i}")
                    d_min_roll = st.number_input("Мин. бросок", 0, 50, 0, key=f"de_min_roll_steal_{i}")
                    dice_payload = {"script_id": "steal_status", "params": {"status": st_steal}}

                elif de_type == "Multiply Status":
                    st_mult_name = st.selectbox("Status", ["smoke", "bleed", "burn"], key=f"de_mul_n_{i}")
                    st_mult_val = st.number_input("Multiplier", 1.5, 4.0, 2.0, step=0.5, key=f"de_mul_v_{i}")
                    st_mult_tgt = st.radio("Target", ["target", "self"], horizontal=True, key=f"de_mul_t_{i}")
                    dice_payload = {"script_id": "multiply_status",
                                    "params": {"status": st_mult_name, "multiplier": st_mult_val,
                                               "target": st_mult_tgt}}

                elif de_type == "Custom Damage":
                    c_dmg_type = st.selectbox("Type", ["stagger", "hp"], key=f"de_cd_t_{i}")
                    c_scale = st.number_input("Scale", 0.0, 10.0, 1.0, step=0.5, key=f"de_cd_s_{i}")
                    c_tgt = st.selectbox("Target", ["target", "self", "all"], key=f"de_cd_tg_{i}")
                    c_prevent = st.checkbox("No Normal Dmg", value=True, key=f"de_cd_p_{i}")
                    dice_payload = {"script_id": "deal_custom_damage",
                                    "params": {"type": c_dmg_type, "scale": c_scale, "target": c_tgt,
                                               "prevent_standard": c_prevent}}

                # Безопасное добавление min_roll
                if dice_payload and d_min_roll > 0:
                    if "params" not in dice_payload: dice_payload["params"] = {}
                    dice_payload["params"]["min_roll"] = int(d_min_roll)

                if dice_payload:
                    d_scripts[de_trig] = [dice_payload]

            type_enum = DiceType[dtype_str.upper()]
            dice_obj = Dice(d_min, d_max, type_enum)
            dice_obj.scripts = d_scripts
            dice_data.append(dice_obj)

    # === 4. СОХРАНЕНИЕ ===
    st.divider()
    save_col, _ = st.columns([1, 4])

    if save_col.button("💾 Сохранить Карту", type="primary"):
        if not name:
            st.error("Введите имя карты!")
        else:
            # Если мы редактировали загруженную карту, используем её старый ID для перезаписи
            # Если это "Новая карта", генерируем новый ID
            card_id = st.session_state.get("ed_loaded_id", None)

            if not card_id:
                card_id = name.lower().replace(" ", "_") + "_" + str(uuid.uuid4())[:4]

            new_card = Card(
                id=card_id,
                name=name,
                tier=tier,
                card_type=ctype,
                description=desc,
                dice_list=dice_data,
                scripts=card_scripts
            )

            Library.save_card(new_card, filename="custom_cards.json")
            st.toast(f"Карта '{name}' сохранена!", icon="✅")