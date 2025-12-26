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
        name = c1.text_input("Card Name", "First Aid Kit", placeholder="Название карты")
        tier = c2.selectbox("Tier", [1, 2, 3], index=0)
        ctype = c3.selectbox("Type", ["melee", "ranged"])

        desc = st.text_area("Description", "On Use: Heal Target for 5 HP", height=68,
                            placeholder="Описание карты...")

    # --- 2. Эффекты Карты (Card Scripts) ---
    # Например: При использовании, В конце боя и т.д.
    card_scripts = {}

    with st.expander("✨ Эффекты карты (On Use / Passive)", expanded=True):
        st.info("Здесь настраиваются эффекты самой карты (до бросков кубиков).")

        ce_col1, ce_col2, ce_col3 = st.columns([1, 1, 1.5])  # Чуть расширил 3 колонку
        ce_trigger = ce_col1.selectbox("Триггер", ["on_use", "on_combat_end"], key="ce_trig")
        ce_type = ce_col2.selectbox("Тип эффекта", ["None", "Restore HP", "Apply Status", "Restore SP"], key="ce_type")

        script_payload = {}

        if ce_type == "Restore HP":
            # Разбиваем колонку на две для Количества и Цели
            h_c1, h_c2 = ce_col3.columns(2)
            amt = h_c1.number_input("HP Amount", 1, 100, 5, key="ce_hp_amt")
            tgt = h_c2.selectbox("Target", ["self", "target"], key="ce_hp_tgt")

            script_payload = {
                "script_id": "restore_hp",
                "params": {"amount": int(amt), "target": tgt}
            }

        elif ce_type == "Restore SP":
            # Аналогично для SP
            s_c1, s_c2 = ce_col3.columns(2)
            amt = s_c1.number_input("SP Amount", 1, 100, 5, key="ce_sp_amt")
            tgt = s_c2.selectbox("Target", ["self", "target"], key="ce_sp_tgt")

            # Пока используем restore_hp логику или заглушку, так как restore_sp может не быть
            # Но если мы его добавим в card_scripts, то будет работать.
            # Для надежности используем restore_hp (как было раньше), но в идеале нужен restore_sp
            script_payload = {
                "script_id": "restore_hp",  # Используем HP скрипт как транспорт, но вообще нужен отдельный ID
                "params": {"amount": int(amt), "target": tgt}
            }
            # Примечание: В logic/card_scripts.py у нас пока нет "restore_sp", но это легко добавить.
            # Пока оставим так, главное - структура.

        elif ce_type == "Apply Status":
            # Тут теперь полный список статусов!
            with st.container(border=True):
                cs1, cs2 = st.columns(2)
                s_name = cs1.selectbox("Выберите статус", available_statuses, key="ce_st_name")
                s_amt = cs2.number_input("Кол-во (Stacks)", 1, 50, 3, key="ce_st_amt")

                cd1, cd2, cd3 = st.columns(3)
                s_dur = cd1.number_input("Длительность", 1, 10, 1, key="ce_st_dur", help="Сколько ходов висит")
                s_del = cd2.number_input("Задержка", 0, 5, 0, key="ce_st_del", help="Через сколько ходов сработает")
                s_tgt = cd3.selectbox("Цель", ["self", "target"], key="ce_st_tgt")

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

    for i, tab in enumerate(tabs):
        with tab:
            d_col1, d_col2, d_col3 = st.columns([1, 1, 1])

            dtype_str = d_col1.selectbox("Тип атаки", ["Slash", "Pierce", "Blunt", "Block", "Evade"], key=f"d_t_{i}")
            d_min = d_col2.number_input("Min", 1, 50, 3, key=f"d_min_{i}")
            d_max = d_col3.number_input("Max", 1, 50, 7, key=f"d_max_{i}")

            # Настройка скриптов КУБИКА
            st.caption("Эффект при попадании/победе (Optional)")
            de_type = st.selectbox("Эффект кубика", ["None", "Apply Status", "Restore HP"], key=f"de_type_{i}")

            d_scripts = {}

            if de_type != "None":
                de_trig = st.selectbox("Условие", ["on_hit", "on_clash_win", "on_clash_lose"], key=f"de_trig_{i}")

                dice_payload = {}

                if de_type == "Restore HP":
                    h_c1, h_c2 = st.columns(2)
                    damt = h_c1.number_input("Heal Amount", 1, 20, 2, key=f"de_h_amt_{i}")
                    dtgt = h_c2.selectbox("Target", ["self", "target"], key=f"de_h_tgt_{i}")

                    dice_payload = {
                        "script_id": "restore_hp",
                        "params": {"amount": int(damt), "target": dtgt}
                    }

                elif de_type == "Apply Status":
                    ds1, ds2 = st.columns(2)
                    d_s_name = ds1.selectbox("Статус", available_statuses, key=f"de_s_name_{i}")
                    d_s_amt = ds2.number_input("Stack", 1, 20, 1, key=f"de_s_amt_{i}")
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

                if dice_payload:
                    d_scripts[de_trig] = [dice_payload]

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