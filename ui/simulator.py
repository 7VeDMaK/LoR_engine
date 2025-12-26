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
# === ИМПОРТ ОБОИХ РЕЕСТРОВ ===
from logic.passives import PASSIVE_REGISTRY
from logic.talents import TALENT_REGISTRY

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
    """Бросок кубиков скорости."""
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']

    p1.recalculate_stats()
    p2.recalculate_stats()

    def process_roll(unit):
        if unit.is_staggered():
            unit.active_slots = [{
                'speed': 0,
                'card': None,
                'target_slot': -1,
                'is_aggro': False,
                'force_clash': False,  # <--- Добавлен флаг (Гедонизм/Принудительный бой)
                'stunned': True
            }]
        else:
            unit.roll_speed_dice()
            # Инициализируем флаг для всех новых слотов
            for s in unit.active_slots:
                s['force_clash'] = False

    process_roll(p1)
    process_roll(p2)

    # Авто-назначение целей
    max_len = max(len(p1.active_slots), len(p2.active_slots))
    for i in range(max_len):
        if i < len(p1.active_slots) and not p1.active_slots[i].get('stunned'):
            target = i if i < len(p2.active_slots) else -1
            p1.active_slots[i]['target_slot'] = target

        if i < len(p2.active_slots) and not p2.active_slots[i].get('stunned'):
            target = i if i < len(p1.active_slots) else -1
            p2.active_slots[i]['target_slot'] = target

    st.session_state['phase'] = 'planning'
    st.session_state['turn_message'] = "🎲 Speed Rolled!"


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
    if p1.active_slots and p1.active_slots[0].get('stunned'):
        p1.current_stagger = p1.max_stagger
        msg.append(f"✨ {p1.name} recovered from Stagger!")

    if p2.active_slots and p2.active_slots[0].get('stunned'):
        p2.current_stagger = p2.max_stagger
        msg.append(f"✨ {p2.name} recovered from Stagger!")

    if not msg:
        if p1.is_staggered(): msg.append(f"{p1.name} is Staggered!")
        if p2.is_staggered(): msg.append(f"{p2.name} is Staggered!")

    st.session_state['turn_message'] = " ".join(msg) if msg else "Turn Complete."

    def trigger_end(unit, prefix):
        logs = []
        for pid in unit.passives:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_round_end(unit, lambda m: logs.append(m))

        for pid in unit.talents:
            if pid in TALENT_REGISTRY: TALENT_REGISTRY[pid].on_round_end(unit, lambda m: logs.append(m))

        status_logs = StatusManager.process_turn_end(unit)
        logs.extend(status_logs)
        unit.tick_cooldowns()

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
            u.active_slots = []
            u.cooldowns = {}
            u.active_buffs = {}
            u.memory = {}

    st.session_state['battle_logs'] = []
    st.session_state['script_logs'] = ""
    st.session_state['turn_message'] = ""
    st.session_state['phase'] = 'roll'


def precalculate_interactions(p1: Unit, p2: Unit):
    ClashSystem.calculate_redirections(p1, p2)
    ClashSystem.calculate_redirections(p2, p1)

    def _calc_ui(me, enemy):
        for i, my_slot in enumerate(me.active_slots):
            if my_slot.get('stunned'):
                my_slot['ui_status'] = {"text": "😵 STAGGERED", "icon": "❌", "color": "gray"}
                continue

            target_idx = my_slot.get('target_slot', -1)
            status = {"text": "⛔ NO TARGET", "icon": "⛔", "color": "gray"}

            if target_idx != -1 and target_idx < len(enemy.active_slots):
                enemy_slot = enemy.active_slots[target_idx]
                if enemy_slot.get('target_slot') == i:
                    status = {"text": f"CLASH S{target_idx + 1}", "icon": "⚔️", "color": "red"}
                else:
                    status = {"text": f"ATK S{target_idx + 1}", "icon": "🏹", "color": "orange"}

            my_slot['ui_status'] = status

    _calc_ui(p1, p2)
    _calc_ui(p2, p1)


# === ИСПРАВЛЕННАЯ ФУНКЦИЯ ОТРИСОВКИ СЛОТА ===
def render_slot_strip(unit: Unit, opponent: Unit, slot_idx: int, key_prefix: str):
    slot = unit.active_slots[slot_idx]

    if slot.get('stunned'):
        with st.container(border=True):
            st.error(f"😵 **UNIT STAGGERED** (Speed 0)")
            st.caption("Персонаж оглушен и пропустит этот ход.")
        return

    # --- АВТО-ВЫБОР КАРТЫ ---
    if unit.deck:
        # Если у юнита есть колода, загружаем только эти карты
        # Используем Library.get_card(id), чтобы получить объекты
        unit_cards = [Library.get_card(cid) for cid in unit.deck]

        # (Опционально) Добавляем карту "Пропуск/Пас", если нужно
        # или проверяем, что карты вообще загрузились
        all_cards = unit_cards if unit_cards else Library.get_all_cards()
    else:
        # Если колода пуста (например, старый персонаж или моб),
        # показываем ВСЕ карты (режим песочницы)
        all_cards = Library.get_all_cards()
    if slot.get('card') is None and all_cards:
        slot['card'] = all_cards[0]

    selected_card = slot.get('card')
    speed = slot['speed']
    ui_stat = slot.get('ui_status', {"text": "...", "icon": "", "color": "gray"})
    card_name = f"🃏 {selected_card.name}" if selected_card else "⚠️ No Page"

    spd_label = f"🎲{speed}"
    if slot.get("source_effect"): spd_label += f" ({slot.get('source_effect')})"

    label = f"S{slot_idx + 1} ({spd_label}) | {ui_stat['icon']} {ui_stat['text']} | {card_name}"

    with st.expander(label, expanded=False):
        # ИЗМЕНЕНИЕ: 3 колонки (Цель, Карта, Опции)
        c_tgt, c_sel, c_opts = st.columns([1.5, 2, 1.2])

        # --- TARGET SELECTOR ---
        target_options = [-1]
        target_labels = {-1: "⛔ None"}
        for i, opp_slot in enumerate(opponent.active_slots):
            target_options.append(i)
            opp_tgt = opp_slot.get('target_slot', -1)
            icon = "⚔️" if opp_tgt == slot_idx else "🛡️"
            extra = "😵" if opp_slot.get('stunned') else f"Spd {opp_slot['speed']}"
            target_labels[i] = f"{icon} S{i + 1} ({extra})"

        current_tgt = slot.get('target_slot', -1)
        if current_tgt not in target_options: current_tgt = -1

        new_target = c_tgt.selectbox(
            "Target", target_options,
            format_func=lambda x: target_labels[x],
            index=target_options.index(current_tgt),
            key=f"{key_prefix}_tgt_{slot_idx}",
            label_visibility="collapsed"
        )
        slot['target_slot'] = new_target

        # --- CARD SELECTOR ---
        card_index = 0
        if selected_card:
            for idx, c in enumerate(all_cards):
                if c.name == selected_card.name:
                    card_index = idx
                    break

        picked_card = c_sel.selectbox(
            "Page", all_cards,
            format_func=lambda x: x.name,
            index=card_index,
            key=f"{key_prefix}_lib_{slot_idx}",
            label_visibility="collapsed"
        )

        if picked_card:
            slot['card'] = picked_card
            selected_card = picked_card

        # --- OPTIONS (AGGRO & FORCE CLASH) ---
        # Делим колонку опций на две маленькие
        opt_c1, opt_c2 = c_opts.columns(2)

        slot['is_aggro'] = opt_c1.checkbox("✋", value=slot.get('is_aggro', False),
                                           key=f"{key_prefix}_aggro_{slot_idx}",
                                           help="Aggro (Перехват)")

        # Галочка "No Discard" (Замочек)
        slot['force_clash'] = opt_c2.checkbox("🔒", value=slot.get('force_clash', False),
                                              key=f"{key_prefix}_force_{slot_idx}",
                                              help="No Discard: Не сбрасывать атаку, даже если я намного быстрее. (Принудительный клэш)")

        st.divider()

        # --- ОТРИСОВКА КУБИКОВ ---
        if selected_card:
            if selected_card.dice_list:
                dice_display = []
                for d in selected_card.dice_list:
                    icon = TYPE_ICONS.get(d.dtype, "?")
                    color = TYPE_COLORS.get(d.dtype, "black")
                    dice_display.append(f":{color}[{icon} {d.min_val}-{d.max_val}]")
                st.markdown(" ".join(dice_display))

            desc_text = []
            if "on_use" in selected_card.scripts:
                for s in selected_card.scripts["on_use"]:
                    desc_text.append(f"On Use: {_format_script_text(s['script_id'], s.get('params', {}))}")

            for d in selected_card.dice_list:
                if d.scripts:
                    for trig, effs in d.scripts.items():
                        for e in effs:
                            t_name = trig.replace("_", " ").title()
                            desc_text.append(f"{t_name}: {_format_script_text(e['script_id'], e.get('params', {}))}")

            if selected_card.description:
                st.caption(f"📝 {selected_card.description}")

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


def render_simulator_page():
    if 'phase' not in st.session_state:
        st.session_state['phase'] = 'roll'

    st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }
        h2 { margin-top: 0 !important; padding-top: 0 !important; }
        [data-testid="stImage"] img { 
            object-fit: cover; 
            border-radius: 12px; 
            width: 100%;
            max-height: 200px !important;
        }
        /* Уменьшаем отступы в экспандерах */
        .streamlit-expanderContent { padding-top: 5px !important; }
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

    precalculate_interactions(p1, p2)

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

    if st.session_state['phase'] == 'roll':
        st.divider()
        ab_c1, ab_c2 = st.columns(2, gap="medium")
        with ab_c1: render_active_abilities(p1, "p1")
        with ab_c2: render_active_abilities(p2, "p2")

    st.divider()

    col_act_l, col_act_r = st.columns(2, gap="medium")

    with col_act_l:
        if p1.active_slots:
            st.subheader(f"Actions ({len(p1.active_slots)})")
            for i in range(len(p1.active_slots)):
                render_slot_strip(p1, p2, i, "p1")
        elif st.session_state['phase'] == 'planning':
            st.warning("No slots!")

    with col_act_r:
        if p2.active_slots:
            st.subheader(f"Actions ({len(p2.active_slots)})")
            for i in range(len(p2.active_slots)):
                render_slot_strip(p2, p1, i, "p2")

    st.divider()

    btn_col = st.columns([1, 2, 1])[1]
    with btn_col:
        if st.session_state['phase'] == 'roll':
            st.button("🎲 ROLL SPEED INITIATIVE", type="primary", on_click=roll_phase, width='stretch')
        else:
            st.button("⚔️ EXECUTE TURN", type="primary", on_click=execute_combat, width='stretch')

    st.subheader("📜 Battle Report")
    if st.session_state.get('turn_message'):
        st.info(st.session_state['turn_message'])

    if st.session_state.get('battle_logs'):
        for log in st.session_state['battle_logs']:
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 2, 4])
                c1.markdown(f"**{log.get('round')}**")
                c2.caption(log.get('rolls'))
                # Использование markdown позволяет отображать жирный шрифт и переносы строк в логах
                c3.markdown(log.get('details'))