# ui/simulator.py
import streamlit as st
import sys
import random
import os
from io import StringIO
from contextlib import contextmanager

from core.models import Card
from logic.clash import ClashSystem
from logic.statuses import StatusManager
from logic.passives import PASSIVE_REGISTRY
from ui.components import render_unit_stats, render_combat_info, card_selector_ui, render_card_visual


@contextmanager
def capture_output():
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

    # === РАСЧЕТ СКОРОСТИ ===
    p1_init_bonus = p1.modifiers.get("initiative", 0)
    p2_init_bonus = p2.modifiers.get("initiative", 0)

    sp1 = random.randint(1, 6) + p1.get_status("haste") - p1.get_status("slow") + p1_init_bonus
    sp2 = random.randint(1, 6) + p2.get_status("haste") - p2.get_status("slow") + p2_init_bonus
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
    def trigger_end_round_passives(unit):
        logs = []
        for pid in unit.passives + unit.talents:
            if pid in PASSIVE_REGISTRY:
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

    # === КОНЕЦ ХОДА (Статусы) ===
    end_turn_logs_p1 = StatusManager.process_turn_end(p1)
    end_turn_logs_p2 = StatusManager.process_turn_end(p2)

    if end_turn_logs_p1:
        st.session_state['battle_logs'].append(
            {"round": "End", "rolls": "P1 Statuses", "details": ", ".join(end_turn_logs_p1)})
    if end_turn_logs_p2:
        st.session_state['battle_logs'].append(
            {"round": "End", "rolls": "P2 Statuses", "details": ", ".join(end_turn_logs_p2)})


def reset_game():
    """Сбрасывает логи и лечит персонажей"""
    # 1. Лечим бойцов (Attacker и Defender)
    for key in ['attacker', 'defender']:
        if key in st.session_state:
            u = st.session_state[key]
            # Восстанавливаем статы до максимума
            u.recalculate_stats()  # На всякий случай обновляем максы
            u.current_hp = u.max_hp
            u.current_stagger = u.max_stagger
            u.current_sp = u.max_sp

            # Очищаем статусы (кровотечение, силу и т.д.)
            u._status_effects = {}
            u.delayed_queue = []

            # Очищаем память пассивок (чтобы забыть старый полученный урон и т.д.)
            u.memory = {}

    # 2. Чистим логи интерфейса
    st.session_state['battle_logs'] = []
    st.session_state['script_logs'] = ""
    st.session_state['turn_message'] = ""


def render_simulator_page():
    # --- CSS MAGIC ---
    # 1. Уменьшаем отступ сверху (block-container)
    # 2. Фиксируем картинки
    st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
        }
        h2 {
            margin-top: 0 !important;
            padding-top: 0 !important;
            margin-bottom: 0.5rem !important;
        }
        [data-testid="stImage"] img {
            max-height: 180px;
            object-fit: cover;
            border-radius: 12px;
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

    st.header("⚔️ Battle Simulator")

    with st.sidebar:
        st.divider()
        st.button("🔄 Reset Battle & Heal", on_click=reset_game, type="secondary", help="Full heal & clear logs")

    col_left, col_right = st.columns(2, gap="large")
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']

    p1.recalculate_stats()
    p2.recalculate_stats()

    # --- ЛЕВАЯ СТОРОНА (АТАКУЮЩИЙ) ---
    with col_left:
        c_avatar, c_stats = st.columns([1, 2])
        with c_avatar:
            img1 = p1.avatar if p1.avatar and os.path.exists(
                p1.avatar) else "https://placehold.co/300x300/png?text=Unit+1"
            st.image(img1, use_container_width=True)
        with c_stats:
            render_unit_stats(p1)

        render_combat_info(p1)
        vis_card_1 = card_selector_ui(p1, "p1")
        render_card_visual(vis_card_1, p1.is_staggered())

    # --- ПРАВАЯ СТОРОНА (ЗАЩИТНИК) ---
    with col_right:
        c_stats, c_avatar = st.columns([2, 1])
        with c_stats:
            render_unit_stats(p2)
        with c_avatar:
            img2 = p2.avatar if p2.avatar and os.path.exists(
                p2.avatar) else "https://placehold.co/300x300/png?text=Unit+2"
            st.image(img2, use_container_width=True)

        render_combat_info(p2)
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