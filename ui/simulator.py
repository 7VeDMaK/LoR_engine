# ui/simulator.py
import streamlit as st
import sys
import random
from io import StringIO
from contextlib import contextmanager

from core.models import Card
from logic.clash import ClashSystem
from logic.statuses import StatusManager
from logic.passives import PASSIVE_REGISTRY  # <--- ВАЖНЫЙ ИМПОРТ
from ui.components import render_unit_stats, render_resist_inputs, card_selector_ui, render_card_visual


@contextmanager
def capture_output():
    """Перехватывает print() из скриптов для отображения в UI"""
    new_out = StringIO()
    old_out = sys.stdout
    try:
        sys.stdout = new_out
        yield new_out
    finally:
        sys.stdout = old_out


def run_combat():
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']

    # --- ФАЗА: ПРОВЕРКА СОСТОЯНИЯ ---
    p1_stag = p1.is_staggered()
    p2_stag = p2.is_staggered()

    real_card_1 = p1.current_card
    real_card_2 = p2.current_card

    if p1_stag: p1.current_card = Card(name="Stunned", dice_list=[])
    if p2_stag: p2.current_card = Card(name="Stunned", dice_list=[])

    sys_clash = ClashSystem()

    # === ВРЕМЕННЫЙ РАСЧЕТ СКОРОСТИ ===
    sp1 = random.randint(1, 6) + p1.get_status("haste") - p1.get_status("slow")
    sp2 = random.randint(1, 6) + p2.get_status("haste") - p2.get_status("slow")
    diff = max(1, sp1) - max(1, sp2)

    adv_p1 = "normal"
    adv_p2 = "normal"

    if diff >= 8:
        adv_p2 = "impossible"
    elif diff >= 4:
        adv_p2 = "disadvantage"
    elif diff <= -8:
        adv_p1 = "impossible"
    elif diff <= -4:
        adv_p1 = "disadvantage"

    with capture_output() as captured:
        logs = sys_clash.resolve_card_clash(p1, p2, adv_p1, adv_p2)

    st.session_state['battle_logs'] = logs
    st.session_state['script_logs'] = captured.getvalue()

    msg = []
    if p1_stag:
        p1.current_stagger = p1.max_stagger
        msg.append(f"{p1.name} recovered!")
    if p2_stag:
        p2.current_stagger = p2.max_stagger
        msg.append(f"{p2.name} recovered!")

    st.session_state['turn_message'] = " ".join(msg)

    if p1_stag: p1.current_card = real_card_1
    if p2_stag: p2.current_card = real_card_2

    # === КОНЕЦ ХОДА (Пассивки/Таланты) ===
    # Сначала срабатывают таланты (например, начислить силу за потерянное ХП)
    def trigger_end_round_passives(unit):
        logs = []
        for pid in unit.passives + unit.talents:
            if pid in PASSIVE_REGISTRY:
                # Передаем unit и функцию-логгер
                PASSIVE_REGISTRY[pid].on_round_end(unit, lambda m: logs.append(m))
        return logs

    pass_logs_p1 = trigger_end_round_passives(p1)
    pass_logs_p2 = trigger_end_round_passives(p2)

    if pass_logs_p1:
        st.session_state['battle_logs'].append(
            {"round": "End", "rolls": "P1 Talents", "details": ", ".join(pass_logs_p1)})
    if pass_logs_p2:
        st.session_state['battle_logs'].append(
            {"round": "End", "rolls": "P2 Talents", "details": ", ".join(pass_logs_p2)})

    # === КОНЕЦ ХОДА (Уменьшение длительности статусов) ===
    # Вызываем после талантов, чтобы только что полученные статусы (Delay=0, Dur=2)
    # корректно уменьшили Duration на 1 и перешли в следующий ход.
    end_turn_logs_p1 = StatusManager.process_turn_end(p1)
    end_turn_logs_p2 = StatusManager.process_turn_end(p2)

    if end_turn_logs_p1:
        st.session_state['battle_logs'].append(
            {"round": "End", "rolls": "P1 Statuses", "details": ", ".join(end_turn_logs_p1)})
    if end_turn_logs_p2:
        st.session_state['battle_logs'].append(
            {"round": "End", "rolls": "P2 Statuses", "details": ", ".join(end_turn_logs_p2)})


def reset_game():
    del st.session_state['attacker']
    del st.session_state['defender']
    st.session_state['battle_logs'] = []
    st.session_state['script_logs'] = ""
    st.session_state['turn_message'] = ""


def render_simulator_page():
    st.header("⚔️ Battle Simulator")

    with st.sidebar:
        st.divider()
        st.button("🔄 Reset Battle", on_click=reset_game, type="secondary")

    col_left, col_right = st.columns(2)
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']

    with col_left:
        render_unit_stats(p1)
        render_resist_inputs(p1, "p1")
        vis_card_1 = card_selector_ui(p1, "p1")
        render_card_visual(vis_card_1, p1.is_staggered())

    with col_right:
        render_unit_stats(p2)
        render_resist_inputs(p2, "p2")
        vis_card_2 = card_selector_ui(p2, "p2")
        render_card_visual(vis_card_2, p2.is_staggered())

    st.divider()

    btn_col = st.columns([1, 2, 1])[1]
    with btn_col:
        label = "🔥 CLASH START 🔥"
        if p1.is_staggered() or p2.is_staggered():
            label = "⚔️ ONE-SIDED ATTACK"
        st.button(label, type="primary", on_click=run_combat, use_container_width=True)

    st.subheader("📜 Battle Report")
    if st.session_state['turn_message']:
        st.success(st.session_state['turn_message'])

    if st.session_state['script_logs']:
        with st.expander("🛠️ Script & Effect Logs (Debug)", expanded=True):
            st.markdown(
                f"<div class='script-log'>{st.session_state['script_logs'].replace(chr(10), '<br>')}</div>",
                unsafe_allow_html=True)

    if st.session_state['battle_logs']:
        for log in st.session_state['battle_logs']:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 4])
                c1.markdown(f"**Round {log.get('round', '?')}**")
                c1.code(log.get('rolls', '0 vs 0'))
                det = log.get('details', '')

                if "Win" in det:
                    c3.write(f"⚔️ {det}")
                elif "One-Sided" in det:
                    c3.error(det)
                elif "Stagger" in det:
                    c3.warning(det)
                elif "Start" in str(log.get('round')):
                    c3.info(det)
                elif "End" in str(log.get('round')):
                    c3.caption(det)
                else:
                    c3.info(det)