import streamlit as st
from core.models import Unit
from core.library import Library
from logic.passives import PASSIVE_REGISTRY
from logic.talents import TALENT_REGISTRY
from ui.components import _format_script_text
from ui.styles import TYPE_ICONS, TYPE_COLORS

def render_slot_strip(unit: Unit, opponent: Unit, slot_idx: int, key_prefix: str):
    slot = unit.active_slots[slot_idx]

    # --- 1. ЕСЛИ ПЕРСОНАЖ ОГЛУШЕН (STAGGER) ---
    if slot.get('stunned'):
        with st.container(border=True):
            st.error(f"😵 **UNIT STAGGERED** (Speed 0)")
            st.caption("Персонаж оглушен и пропустит этот ход. Получаемый урон увеличен.")
        return

    # --- 2. ПОДГОТОВКА ЗАГОЛОВКА ---
    speed = slot['speed']
    ui_stat = slot.get('ui_status', {"text": "...", "icon": "", "color": "gray"})
    selected_card = slot.get('card')
    card_name = f"🃏 {selected_card.name}" if selected_card else "⚠️ No Page"

    # Если слот создан талантом (например, Ярость или Неистовство), покажем это
    spd_label = f"🎲{speed}"
    if slot.get("source_effect"):
        spd_label += f" ({slot.get('source_effect')})"

    label = f"S{slot_idx + 1} ({spd_label}) | {ui_stat['icon']} {ui_stat['text']} | {card_name}"

    # --- 3. РАСКРЫВАЮЩАЯСЯ ПАНЕЛЬ СЛОТА ---
    with st.expander(label, expanded=False):
        c_tgt, c_sel, c_aggro = st.columns([1.5, 2, 0.5])

        # === КОЛОНКА 1: ВЫБОР ЦЕЛИ ===
        target_options = [-1]
        target_labels = {-1: "⛔ None"}

        for i, opp_slot in enumerate(opponent.active_slots):
            target_options.append(i)
            opp_tgt = opp_slot.get('target_slot', -1)

            # Иконка показывает, целятся ли в нас в ответ
            icon = "⚔️" if opp_tgt == slot_idx else "🛡️"

            # Инфо о скорости врага
            opp_spd = opp_slot['speed']
            extra = "😵" if opp_slot.get('stunned') else f"Spd {opp_spd}"

            target_labels[i] = f"{icon} S{i + 1} ({extra})"

        current_tgt = slot.get('target_slot', -1)
        if current_tgt not in target_options: current_tgt = -1

        c_tgt.selectbox(
            "Target", target_options,
            format_func=lambda x: target_labels[x],
            index=target_options.index(current_tgt),
            key=f"{key_prefix}_tgt_{slot_idx}",
            label_visibility="collapsed",
            help="Выберите слот противника для атаки"
        )

        # === КОЛОНКА 2: ВЫБОР КАРТЫ (С УЧЕТОМ БЛОКИРОВКИ) ===
        # Если слот 'locked' (например, от таланта Неистовство), мы не даем менять карту
        if slot.get('locked', False):
            locked_name = selected_card.name if selected_card else "Locked Ability"
            c_sel.warning(f"🔒 {locked_name}")
        else:
            # Обычный выбор из библиотеки
            all_cards = Library.get_all_cards()
            card_index = 0
            if selected_card:
                for idx, c in enumerate(all_cards):
                    if c.name == selected_card.name:
                        card_index = idx
                        break

            c_sel.selectbox(
                "Page", all_cards,
                format_func=lambda x: x.name,
                index=card_index,
                key=f"{key_prefix}_lib_{slot_idx}",
                label_visibility="collapsed"
            )

        # === КОЛОНКА 3: АГГРО ЧЕКБОКС ===
        c_aggro.checkbox("✋", value=slot.get('is_aggro', False),
                         key=f"{key_prefix}_aggro_{slot_idx}",
                         help="Попытаться перехватить атаку (Aggro)")

        st.divider()

        # === 4. ОТОБРАЖЕНИЕ ИНФОРМАЦИИ О КАРТЕ ===
        if selected_card:
            # Кубики
            if selected_card.dice_list:
                dice_display = []
                for d in selected_card.dice_list:
                    icon = TYPE_ICONS.get(d.dtype, "?")
                    color = TYPE_COLORS.get(d.dtype, "black")
                    dice_display.append(f":{color}[{icon} {d.min_val}-{d.max_val}]")
                st.markdown(" ".join(dice_display))

            # Сбор описания скриптов для подсказки
            desc_text = []

            # Эффекты "При использовании"
            if "on_use" in selected_card.scripts:
                for s in selected_card.scripts["on_use"]:
                    desc_text.append(f"On Use: {_format_script_text(s['script_id'], s.get('params', {}))}")

            # Эффекты кубиков (При попадании / При победе)
            for d in selected_card.dice_list:
                if d.scripts:
                    for trig, effs in d.scripts.items():
                        for e in effs:
                            t_name = trig.replace("_", " ").title()
                            desc_text.append(f"{t_name}: {_format_script_text(e['script_id'], e.get('params', {}))}")

            # Описание самой карты
            if selected_card.description:
                st.caption(f"📝 {selected_card.description}")

            # Вывод списка эффектов
            if desc_text:
                for line in desc_text:
                    st.caption(f"• {line}")

def render_active_abilities(unit, unit_key):
    abilities = []
    for pid in unit.passives:
        if pid in PASSIVE_REGISTRY: abilities.append((pid, PASSIVE_REGISTRY[pid]))
    for pid in unit.talents:
        if pid in TALENT_REGISTRY: abilities.append((pid, TALENT_REGISTRY[pid]))

    has_actives = False
    for pid, obj in abilities:
        if getattr(obj, "is_active_ability", False):
            has_actives = True

            # Контейнер для одной способности
            with st.container(border=True):
                cd = unit.cooldowns.get(pid, 0)
                active_dur = unit.active_buffs.get(pid, 0)

                # Проверяем, есть ли опции выбора (как у Smoke Universality)
                options = getattr(obj, "conversion_options", None)
                selected_opt = None

                # Заголовок
                st.markdown(f"**{obj.name}**")

                if options:
                    # Рисуем выбор
                    selected_opt = st.selectbox(
                        "Effect",
                        options.keys(),
                        key=f"sel_{unit_key}_{pid}",
                        label_visibility="collapsed"
                    )

                # Кнопка активации
                btn_label = "Activate"
                disabled = False

                if active_dur > 0:
                    btn_label = f"Active ({active_dur})"
                    disabled = True
                elif cd > 0:
                    btn_label = f"Cooldown ({cd})"
                    disabled = True

                if st.button(f"✨ {btn_label}", key=f"act_{unit_key}_{pid}", disabled=disabled,
                             use_container_width=True):
                    def log_f(msg):
                        st.session_state.get('battle_logs', []).append(
                            {"round": "Skill", "rolls": "Activate", "details": msg})

                    # Если была выбрана опция, передаем её в activate
                    if options:
                        if obj.activate(unit, log_f, choice_key=selected_opt):
                            st.rerun()
                    else:
                        # Обычная активация без параметров
                        if obj.activate(unit, log_f):
                            st.rerun()

    if has_actives: st.caption("Active Abilities")