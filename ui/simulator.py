# ui/simulator.py
import streamlit as st
import sys
import random
import os
from io import StringIO
from contextlib import contextmanager

from core.models import Card, Unit, DiceType
from core.library import Library
from logic.clash import ClashSystem
from logic.statuses import StatusManager
from logic.passives import PASSIVE_REGISTRY
from ui.components import render_unit_stats, render_combat_info, _format_script_text
from ui.styles import TYPE_ICONS, TYPE_COLORS


@contextmanager
def capture_output():
    new_out = StringIO()
    old_out = sys.stdout
    try:
        sys.stdout = new_out
        yield new_out
    finally:
        sys.stdout = old_out


def roll_phase():
    """Бросок кубиков скорости для обоих"""
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']

    p1.recalculate_stats()
    p2.recalculate_stats()

    p1.roll_speed_dice()
    p2.roll_speed_dice()

    # Авто-назначение целей
    max_len = max(len(p1.active_slots), len(p2.active_slots))
    for i in range(max_len):
        if i < len(p1.active_slots):
            target = i if i < len(p2.active_slots) else -1
            p1.active_slots[i]['target_slot'] = target

        if i < len(p2.active_slots):
            target = i if i < len(p1.active_slots) else -1
            p2.active_slots[i]['target_slot'] = target

    st.session_state['phase'] = 'planning'
    st.session_state['turn_message'] = "🎲 Speed Rolled! Assign Cards & Targets."


def execute_combat():
    """Запуск боя"""
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']

    sys_clash = ClashSystem()

    with capture_output() as captured:
        logs = sys_clash.resolve_turn(p1, p2)

    st.session_state['battle_logs'] = logs
    st.session_state['script_logs'] = captured.getvalue()

    msg = []
    if p1.is_staggered():
        p1.current_stagger = p1.max_stagger
        msg.append(f"{p1.name} recovered!")
    if p2.is_staggered():
        p2.current_stagger = p2.max_stagger
        msg.append(f"{p2.name} recovered!")

    st.session_state['turn_message'] = " ".join(msg) if msg else "Turn Complete."

    def trigger_end(unit, prefix):
        logs = []
        for pid in unit.passives + unit.talents:
            if pid in PASSIVE_REGISTRY:
                PASSIVE_REGISTRY[pid].on_round_end(unit, lambda m: logs.append(m))

        status_logs = StatusManager.process_turn_end(unit)
        logs.extend(status_logs)

        if logs:
            st.session_state['battle_logs'].append(
                {"round": "End", "rolls": f"{prefix} End", "details": ", ".join(logs)})

    trigger_end(p1, "P1")
    trigger_end(p2, "P2")

    p1.active_slots = []
    p2.active_slots = []
    st.session_state['phase'] = 'roll'


def reset_game():
    for key in ['attacker', 'defender']:
        if key in st.session_state:
            u = st.session_state[key]
            u.recalculate_stats()
            u.current_hp = u.max_hp
            u.current_stagger = u.max_stagger
            u.current_sp = u.max_sp
            u._status_effects = {}
            u.delayed_queue = []
            u.memory = {}
            u.active_slots = []

    st.session_state['battle_logs'] = []
    st.session_state['script_logs'] = ""
    st.session_state['turn_message'] = ""
    st.session_state['phase'] = 'roll'


# --- НОВЫЙ РЕНДЕР СЛОТА (ПОЛОСКА) ---
def render_slot_strip(unit: Unit, opponent: Unit, slot_idx: int, key_prefix: str):
    slot = unit.active_slots[slot_idx]
    speed = slot['speed']

    border_color = "red" if speed < 3 else "orange" if speed < 6 else "green"

    with st.container(border=True):
        # ВЕРХНЯЯ ЧАСТЬ: ИНФО СЛОТА И ВЫБОР ЦЕЛИ
        c_head1, c_head2 = st.columns([1, 2])
        c_head1.markdown(f"**Slot {slot_idx + 1}** :{border_color}[🎲{speed}]")

        target_options = [-1]
        target_labels = {-1: "⛔ None"}

        for i, opp_slot in enumerate(opponent.active_slots):
            target_options.append(i)
            is_clashing = (opp_slot.get('target_slot') == slot_idx)
            icon = "⚔️" if is_clashing else "🏹"
            target_labels[i] = f"{icon} S{i + 1} ({opp_slot['speed']})"

        current_tgt = slot.get('target_slot', -1)
        if current_tgt not in target_options: current_tgt = -1

        new_target = c_head2.selectbox(
            "Target", target_options,
            format_func=lambda x: target_labels[x],
            index=target_options.index(current_tgt),
            key=f"{key_prefix}_tgt_{slot_idx}",
            label_visibility="collapsed"
        )
        unit.active_slots[slot_idx]['target_slot'] = new_target

        st.divider()

        # СРЕДНЯЯ ЧАСТЬ: ВЫБОР КАРТЫ
        c_sel, c_aggro = st.columns([3, 1])
        all_cards = Library.get_all_cards()

        selected_card = c_sel.selectbox(
            "Page", all_cards,
            format_func=lambda x: x.name,
            key=f"{key_prefix}_lib_{slot_idx}",
            label_visibility="collapsed",
            placeholder="Select Page..."
        )

        is_aggro = c_aggro.checkbox("✋", value=slot.get('is_aggro', False),
                                    key=f"{key_prefix}_aggro_{slot_idx}",
                                    help="Aggro: Принудительный перехват")

        if not unit.is_staggered():
            unit.active_slots[slot_idx]['card'] = selected_card
            unit.active_slots[slot_idx]['is_aggro'] = is_aggro

        # НИЖНЯЯ ЧАСТЬ: ДЕТАЛИ КАРТЫ (Типы атак и Описание)
        if selected_card:
            # 1. Кубики (Цветные иконки)
            if selected_card.dice_list:
                dice_display = []
                for d in selected_card.dice_list:
                    icon = TYPE_ICONS.get(d.dtype, "?")
                    color = TYPE_COLORS.get(d.dtype, "black")
                    dice_display.append(f":{color}[{icon} {d.min_val}-{d.max_val}]")
                st.markdown(" ".join(dice_display))

            # 2. Описание (Эффекты)
            desc_text = []
            # Скрипты карты (On Use)
            if "on_use" in selected_card.scripts:
                for s in selected_card.scripts["on_use"]:
                    desc_text.append(f"On Use: {_format_script_text(s['script_id'], s.get('params', {}))}")

            # Скрипты кубиков (On Hit и т.д.)
            for d in selected_card.dice_list:
                if d.scripts:
                    for trig, effs in d.scripts.items():
                        for e in effs:
                            t_name = trig.replace("_", " ").title()
                            desc_text.append(f"{t_name}: {_format_script_text(e['script_id'], e.get('params', {}))}")

            # Если есть ручное описание, добавляем его тоже
            if selected_card.description:
                st.caption(f"📝 {selected_card.description}")

            if desc_text:
                for line in desc_text:
                    st.caption(f"• {line}")


def render_simulator_page():
    if 'phase' not in st.session_state:
        st.session_state['phase'] = 'roll'

    st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }
        h2 { margin-top: 0 !important; padding-top: 0 !important; }
        /* Картинка: ограничение 200px */
        [data-testid="stImage"] img { 
            object-fit: cover; 
            border-radius: 12px; 
            width: 100%;
            max-height: 200px !important;
        }
        /* Уменьшаем отступы внутри контейнеров слотов */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            gap: 0.5rem;
        }
        .stDivider { margin-top: 0.5rem; margin-bottom: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)

    st.header("⚔️ Battle Simulator")

    with st.sidebar:
        st.divider()
        st.button("🔄 Reset & Heal", on_click=reset_game, type="secondary")

    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']

    p1.recalculate_stats()
    p2.recalculate_stats()

    col_l, col_r = st.columns(2, gap="medium")

    # --- ЛЕВАЯ СТОРОНА (P1) ---
    with col_l:
        c1, c2 = st.columns([1, 1])
        with c1:
            img = p1.avatar if p1.avatar and os.path.exists(p1.avatar) else "https://placehold.co/150x150/png?text=P1"
            st.image(img, use_container_width=True)
        with c2:
            render_unit_stats(p1)

        render_combat_info(p1)

        if p1.active_slots:
            st.subheader(f"Actions ({len(p1.active_slots)})")
            # Рендерим слоты вертикальным списком
            for i in range(len(p1.active_slots)):
                render_slot_strip(p1, p2, i, "p1")
        elif st.session_state['phase'] == 'planning':
            st.warning("No slots!")

    # --- ПРАВАЯ СТОРОНА (P2) ---
    with col_r:
        c1, c2 = st.columns([1, 1])
        with c1:
            render_unit_stats(p2)
        with c2:
            img = p2.avatar if p2.avatar and os.path.exists(p2.avatar) else "https://placehold.co/150x150/png?text=P2"
            st.image(img, use_container_width=True)

        render_combat_info(p2)

        if p2.active_slots:
            st.subheader(f"Actions ({len(p2.active_slots)})")
            # Рендерим слоты вертикальным списком
            for i in range(len(p2.active_slots)):
                render_slot_strip(p2, p1, i, "p2")

    st.divider()

    btn_col = st.columns([1, 2, 1])[1]
    with btn_col:
        if st.session_state['phase'] == 'roll':
            st.button("🎲 ROLL SPEED INITIATIVE", type="primary", on_click=roll_phase, use_container_width=True)
        else:
            st.button("⚔️ EXECUTE TURN", type="primary", on_click=execute_combat, use_container_width=True)

    # --- REPORT ---
    st.subheader("📜 Battle Report")
    if st.session_state.get('turn_message'):
        st.info(st.session_state['turn_message'])

    st.caption("Легенда: ⚔️ = Clash, 🏹 = One-Sided. ✋ = Aggro (принудительный перехват)")

    if st.session_state.get('battle_logs'):
        for log in st.session_state['battle_logs']:
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 2, 4])
                c1.markdown(f"**{log.get('round')}**")
                c2.caption(log.get('rolls'))
                c3.write(log.get('details'))