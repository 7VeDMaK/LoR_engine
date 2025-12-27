import streamlit as st
import os

from core.models import DiceType
from ui.components import render_unit_stats, render_combat_info
from ui.styles import TYPE_ICONS

# Импорт логики и компонентов из новых файлов
from ui.simulator.simulator_logic import (
    roll_phase, step_start, step_next, step_finish,
    execute_combat_auto, reset_game,
    sync_state_from_widgets, precalculate_interactions
)
from ui.simulator.simulator_components import render_slot_strip, render_active_abilities


def render_simulator_page():
    if 'phase' not in st.session_state: st.session_state['phase'] = 'roll'
    if 'combat_mode' not in st.session_state: st.session_state['combat_mode'] = 'Auto'

    # === ОБНОВЛЕННЫЕ СТИЛИ ===
    st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }

        /* Стили для карточек боя */
        .clash-card-left { text-align: right; padding-right: 10px; }
        .clash-card-right { text-align: left; padding-left: 10px; }

        /* === ФИКС ДЛЯ КАРТИНОК (АВАТАРОК) === */
        [data-testid="stImage"] img {
            max-height: 200px !important; /* Ограничиваем высоту */
            width: auto !important;       /* Ширина подстроится сама */
            object-fit: contain;          /* Картинка не будет обрезаться */
            margin: 0 auto;               /* Центрирование */
            border-radius: 8px;           /* Скругление углов */
        }

        /* Центрирование контейнера картинки */
        [data-testid="stImage"] {
            text-align: center;
            display: flex;
            justify_content: center;
        }
    </style>
    """, unsafe_allow_html=True)

    st.header("⚔️ Battle Simulator")

    with st.sidebar:
        st.divider()
        st.session_state['combat_mode'] = st.radio("Combat Mode", ["Auto (Fast)", "Manual (Step-by-Step)"])
        st.divider()
        st.button("🔄 Reset & Heal", on_click=reset_game, type="secondary")

    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']

    p1.recalculate_stats()
    p2.recalculate_stats()

    if p1.active_slots: sync_state_from_widgets(p1, "p1")
    if p2.active_slots: sync_state_from_widgets(p2, "p2")

    precalculate_interactions(p1, p2)

    # --- ВЕРХНЯЯ ЧАСТЬ: ИНФО О ПЕРСОНАЖАХ ---
    col_info_l, col_info_r = st.columns(2, gap="medium")
    with col_info_l:
        c1, c2 = st.columns([1, 1])
        with c1:
            img = p1.avatar if p1.avatar and os.path.exists(p1.avatar) else "https://placehold.co/150x150/png?text=P1"
            st.image(img, width='stretch')
        with c2: render_unit_stats(p1)
        render_combat_info(p1)

    with col_info_r:
        c1, c2 = st.columns([1, 1])
        with c1: render_unit_stats(p2)
        with c2:
            img = p2.avatar if p2.avatar and os.path.exists(p2.avatar) else "https://placehold.co/150x150/png?text=P2"
            st.image(img, width='stretch')
        render_combat_info(p2)

    # Активные способности (только в фазе броска)
    if st.session_state['phase'] == 'roll':
        st.divider()
        ab_c1, ab_c2 = st.columns(2, gap="medium")
        with ab_c1: render_active_abilities(p1, "p1")
        with ab_c2: render_active_abilities(p2, "p2")

    st.divider()

    # --- СЛОТЫ ДЕЙСТВИЙ ---
    col_act_l, col_act_r = st.columns(2, gap="medium")
    with col_act_l:
        if p1.active_slots:
            st.subheader(f"Actions ({len(p1.active_slots)})")
            for i in range(len(p1.active_slots)): render_slot_strip(p1, p2, i, "p1")
        elif st.session_state['phase'] == 'planning':
            st.warning("No slots!")

    with col_act_r:
        if p2.active_slots:
            st.subheader(f"Actions ({len(p2.active_slots)})")
            for i in range(len(p2.active_slots)): render_slot_strip(p2, p1, i, "p2")

    st.divider()

    # === КНОПКИ УПРАВЛЕНИЯ (ЦЕНТРИРОВАННЫЕ) ===
    # Используем колонки [1, 2, 1], чтобы кнопки были по центру
    _, c_center, _ = st.columns([1, 2, 1])

    with c_center:
        if st.session_state['phase'] == 'roll':
            st.button("🎲 ROLL SPEED INITIATIVE", type="primary", on_click=roll_phase, width='stretch')

        elif st.session_state['phase'] == 'planning':
            if st.session_state['combat_mode'] == 'Auto (Fast)':
                st.button("⚔️ EXECUTE TURN (ALL)", type="primary", on_click=execute_combat_auto, width='stretch')
            else:
                # Ручной режим
                if st.session_state.get('turn_phase') != 'fighting':
                    st.button("🏁 START COMBAT PHASE", type="primary", on_click=step_start, width='stretch')
                else:
                    # Кнопки "Next" и "Finish" внутри центрального блока
                    cn1, cn2 = st.columns([3, 1])
                    actions_left = len(st.session_state['turn_actions']) - st.session_state['action_idx']
                    cn1.button(f"⏩ NEXT ACTION ({actions_left})", type="primary", on_click=step_next, width='stretch')
                    cn2.button("🏁 End", type="secondary", on_click=step_finish, width='stretch')

    # === ВЫВОД ЛОГОВ (СИММЕТРИЧНЫЙ ДИЗАЙН) ===
    st.subheader("📜 Battle Report")

    if st.session_state.get('turn_message'):
        st.info(st.session_state['turn_message'])

    logs = st.session_state.get('battle_logs', [])

    if logs:
        for log in logs:
            if "left" in log:
                with st.container(border=True):
                    left = log['left']
                    right = log['right']

                    # 1. ВИЗУАЛИЗАЦИЯ (ВЕРХНИЙ РЯД)
                    # Пропорции: [2 (P1)] [1 (VS)] [2 (P2)]
                    c_vis_l, c_vis_c, c_vis_r = st.columns([2, 0.8, 2])

                    # P1 (Слева, выравнивание вправо к центру)
                    with c_vis_l:
                        icon = TYPE_ICONS.get(DiceType[left['dice']], "") if left['dice'] != "None" else ""
                        rng = f"[{left['range']}]" if left['range'] != "-" else ""
                        st.markdown(f"""
                        <div class="clash-card-left">
                            <b>{left['unit']}</b> <span style='color:gray; font-size:0.8em'>({left['card']})</span><br>
                            <span style="font-size:1.1em;">{icon} {rng}</span> <b style="font-size:1.4em;">{left['val']}</b>
                        </div>
                        """, unsafe_allow_html=True)

                    # VS (Центр)
                    with c_vis_c:
                        st.markdown(f"""
                        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding-top: 10px;">
                            <span style="color:gray; font-size:0.9em;">VS</span>
                        </div>
                        """, unsafe_allow_html=True)

                    # P2 (Справа, выравнивание влево к центру)
                    with c_vis_r:
                        icon = TYPE_ICONS.get(DiceType[right['dice']], "") if right['dice'] != "None" else ""
                        rng = f"[{right['range']}]" if right['range'] != "-" else ""
                        st.markdown(f"""
                        <div class="clash-card-right">
                            <b style="font-size:1.4em;">{right['val']}</b> <span style="font-size:1.1em;">{rng} {icon}</span><br>
                            <span style='color:gray; font-size:0.8em'>({right['card']})</span> <b>{right['unit']}</b>
                        </div>
                        """, unsafe_allow_html=True)

                    # 2. ОПИСАНИЕ И ЭФФЕКТЫ (НИЖНИЙ РЯД, НА ВСЮ ШИРИНУ)
                    st.divider()  # Тонкая линия разделитель

                    st.caption(f"Round: {log['round']} | {log['outcome']}")

                    effects = [e for e in log['details'] if "[" not in e or "]" not in e]
                    modifiers = [e for e in log['details'] if "[" in e and "]" in e]

                    for eff in effects:
                        st.markdown(f"➤ {eff}")

                    if modifiers:
                        with st.expander("Modifiers", expanded=False):
                            for mod in modifiers: st.caption(mod)

            else:
                # Старый лог (Start/End)
                with st.container():
                    st.caption(f"⏱️ {log.get('round')} | {log.get('details')}")