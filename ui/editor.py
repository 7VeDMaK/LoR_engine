import streamlit as st
import uuid
from core.models import Card, Dice, DiceType
from core.library import Library
# Импортируем реестр статусов, чтобы выпадающий список был живым
from logic.status_definitions import STATUS_REGISTRY


def render_editor_page():
    st.markdown("### 🛠️ Card Creator (Advanced)")

    # Получаем список всех доступных статусов из кода
    available_statuses = sorted(list(STATUS_REGISTRY.keys()))

    # --- 1. Основные параметры ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        name = c1.text_input("Card Name", "", placeholder="Название карты")
        tier = c2.selectbox("Tier", [1, 2, 3], index=0)
        ctype = c3.selectbox("Type", ["melee", "ranged"])

        desc = st.text_area("Description", "", height=68,
                            placeholder="Описание карты...")

    # --- 2. Эффекты Карты (Card Scripts) ---
    # Например: При использовании, В конце боя и т.д.
    card_scripts = {}

    with st.expander("✨ Эффекты карты (On Use / Passive)", expanded=True):
        st.info("Здесь настраиваются эффекты самой карты (до бросков кубиков).")

        ce_col1, ce_col2, ce_col3 = st.columns([1, 1, 1])
        ce_trigger = ce_col1.selectbox("Триггер", ["on_use", "on_combat_end"], key="ce_trig")
        ce_type = ce_col2.selectbox("Тип эффекта", ["None", "Restore HP", "Restore SP", "Apply Status", "Steal Status"], key="ce_type")

        script_payload = {}

        if ce_type == "Restore HP":
            amt = ce_col3.number_input("HP Amount", 1, 100, 5, key="ce_hp_amt")
            script_payload = {
                "script_id": "restore_hp",
                "params": {"amount": int(amt), "target": "self"}
            }

        elif ce_type == "Restore SP":
            # Для SP нам понадобится отдельный скрипт restore_sp, но пока можно использовать restore_hp логику или добавить позже
            # Пока сделаем заглушку через restore_hp (технически можно добавить restore_sp в card_scripts.py)
            amt = ce_col3.number_input("SP Amount", 1, 100, 5, key="ce_sp_amt")
            st.warning("Требуется скрипт restore_sp (пока не реализован, использую HP)")
            script_payload = {
                "script_id": "restore_hp",
                "params": {"amount": int(amt), "target": "self"}
            }

        elif ce_type == "Apply Status":
            # Тут теперь полный список статусов!
            with st.container(border=True):
                cs1, cs2 = st.columns(2)
                s_name = cs1.selectbox("Выберите статус", available_statuses, key="ce_st_name")
                s_amt = cs2.number_input("Кол-во (Stacks)", 1, 50, 3, key="ce_st_amt")

                cd1, cd2, cd3 = st.columns(3)
                s_dur = cd1.number_input("Длительность", 1, 10, 1, key="ce_st_dur", help="Сколько ходов висит")
                s_del = cd2.number_input("Задержка", 0, 5, 0, key="ce_st_del", help="Через сколько ходов сработает")
                s_tgt = cd3.selectbox(
                    "Цель",
                    ["self", "target", "all"],
                    key="ce_st_tgt",
                    format_func=lambda x: "Self + Target" if x == "all" else x.capitalize()
                )

                script_payload = {
                    "script_id": "apply_status",
                    "params": {
                        "status": s_name,
                        "stack": int(s_amt),
                        "duration": int(s_dur),
                        "delay": int(s_del),
                        "target": s_tgt
                    }
                }
        elif ce_type == "Steal Status":
            st_name = ce_col3.selectbox("Status to Steal", ["smoke", "strength", "charge"], key="ce_steal_st")

            script_payload = {
                "script_id": "steal_status",
                "params": {
                    "status": st_name
                }
            }

        if script_payload:
            # Можно добавлять несколько, но пока для простоты один
            card_scripts[ce_trigger] = [script_payload]

    # --- 3. Кубики (Dice) ---
    st.divider()
    st.markdown("**Настройка кубиков**")

    # Сделаем управление количеством кубиков более явным
    num_dice = st.number_input("Количество кубиков", 1, 5, 2)

    dice_data = []

    # Используем tabs для кубиков, чтобы не загромождать экран
    tabs = st.tabs([f"Dice {i + 1}" for i in range(num_dice)])

    # ui/editor.py

    for i, tab in enumerate(tabs):
        with tab:
            d_col1, d_col2, d_col3 = st.columns([1, 1, 1])

            dtype_str = d_col1.selectbox("Тип атаки", ["Slash", "Pierce", "Blunt", "Block", "Evade"], key=f"d_t_{i}")
            d_min = d_col2.number_input("Min", 1, 50, 3, key=f"d_min_{i}")
            d_max = d_col3.number_input("Max", 1, 50, 7, key=f"d_max_{i}")

            st.caption("Эффект при попадании/победе (Optional)")
            de_type = st.selectbox("Эффект кубика", ["None", "Apply Status", "Restore HP", "Steal Status", "Multiply Status", "Custom Damage"],
                                   key=f"de_type_{i}")

            d_scripts = {}
            dice_payload = {}

            # === ИСПРАВЛЕНИЕ: Инициализируем переменную заранее ===
            d_min_roll = 0
            # ======================================================

            if de_type != "None":
                de_trig = st.selectbox("Условие", ["on_hit", "on_clash_win", "on_clash_lose"], key=f"de_trig_{i}")

                if de_type == "Restore HP":
                    damt = st.number_input("Heal Amount", 1, 20, 2, key=f"de_h_amt_{i}")
                    dice_payload = {
                        "script_id": "restore_hp",
                        "params": {"amount": int(damt), "target": "self"}
                    }

                elif de_type == "Apply Status":
                    ds1, ds2 = st.columns(2)
                    d_s_name = ds1.selectbox("Статус", available_statuses, key=f"de_s_name_{i}")
                    d_s_amt = ds2.number_input("Stack", 1, 20, 1, key=f"de_s_amt_{i}")

                    d_min_roll = st.number_input("Мин. бросок", 0, 50, 0, key=f"de_min_roll_{i}")

                    d_tgt = st.radio("Цель", ["target", "self"], horizontal=True, key=f"de_tgt_{i}")

                    dice_payload = {
                        "script_id": "apply_status",
                        "params": {
                            "status": d_s_name,
                            "stack": int(d_s_amt),
                            "duration": 1,
                            "delay": 0,
                            "target": d_tgt
                        }
                    }

                elif de_type == "Steal Status":
                    st_steal = st.selectbox("Status to Steal", ["smoke", "strength", "charge"], key=f"de_steal_{i}")
                    d_min_roll = st.number_input("Мин. бросок", 0, 50, 0, key=f"de_min_roll_steal_{i}")

                    dice_payload = {
                        "script_id": "steal_status",
                        "params": {
                            "status": st_steal
                        }
                    }
                elif de_type == "Multiply Status":
                    st_mult_name = st.selectbox("Status", ["smoke", "bleed", "burn"], key=f"de_mul_n_{i}")
                    st_mult_val = st.number_input("Multiplier", 1.5, 4.0, 2.0, step=0.5, key=f"de_mul_v_{i}")
                    st_mult_tgt = st.radio("Target", ["target", "self"], horizontal=True, key=f"de_mul_t_{i}")

                    dice_payload = {
                        "script_id": "multiply_status",
                        "params": {
                            "status": st_mult_name,
                            "multiplier": st_mult_val,
                            "target": st_mult_tgt
                        }
                    }

                elif de_type == "Custom Damage":
                    c_dmg_type = st.selectbox("Damage Type", ["stagger", "hp"], key=f"de_cd_t_{i}")
                    c_scale = st.number_input("Scale (Multiplier)", 0.0, 10.0, 1.0, step=0.5, key=f"de_cd_s_{i}",
                                              help="Множитель урона от значения кубика")
                    c_tgt = st.selectbox("Target", ["target", "self", "all"], key=f"de_cd_tg_{i}")
                    c_prevent = st.checkbox("Prevent Normal Dmg", value=True, key=f"de_cd_p_{i}",
                                            help="Если включено, обычный урон по HP наноситься не будет")

                    dice_payload = {
                        "script_id": "deal_custom_damage",
                        "params": {
                            "type": c_dmg_type,
                            "scale": c_scale,
                            "target": c_tgt,
                            "prevent_standard": c_prevent
                        }
                    }

                # Безопасное добавление min_roll
                if dice_payload and d_min_roll > 0:
                    if "params" not in dice_payload:
                        dice_payload["params"] = {}
                    dice_payload["params"]["min_roll"] = int(d_min_roll)

                if dice_payload:
                    d_scripts[de_trig] = [dice_payload]

            # Конвертация типа (остальной код без изменений)
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

    if save_col.button("💾 Сохранить Карту", type="primary"):
        if not name:
            st.error("Введите имя карты!")
        else:
            # Генерируем ID
            auto_id = name.lower().replace(" ", "_") + "_" + str(uuid.uuid4())[:4]

            new_card = Card(
                id=auto_id,
                name=name,
                tier=tier,
                card_type=ctype,
                description=desc,
                dice_list=dice_data,
                scripts=card_scripts
            )

            # Сохраняем в кастомный файл
            Library.save_card(new_card, filename="custom_cards.json")
            st.toast(f"Карта '{name}' успешно сохранена!", icon="✅")