import os
import sys
from contextlib import contextmanager
from io import StringIO

import streamlit as st

from core.library import Library
from core.models import Unit, DiceType
from logic.clash import ClashSystem
# === ИМПОРТ ОБОИХ РЕЕСТРОВ ===
from logic.passives import PASSIVE_REGISTRY
from logic.statuses import StatusManager
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


def step_start():
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']
    sys_clash = ClashSystem()

    # 1. Prepare
    init_logs, actions = sys_clash.prepare_turn(p1, p2)

    st.session_state['battle_logs'] = init_logs
    st.session_state['turn_actions'] = actions  # Сохраняем очередь
    st.session_state['executed_p1'] = set()
    st.session_state['executed_p2'] = set()
    st.session_state['turn_phase'] = 'fighting'  # Меняем фазу
    st.session_state['action_idx'] = 0


def step_next():
    actions = st.session_state['turn_actions']
    idx = st.session_state['action_idx']

    if idx < len(actions):
        sys_clash = ClashSystem()
        act = actions[idx]

        # Важно: объекты юнитов в act['unit'] — это ссылки на p1/p2 в памяти,
        # так что изменения HP применятся к реальным объектам сессии.

        logs = sys_clash.execute_single_action(
            act,
            st.session_state['executed_p1'],
            st.session_state['executed_p2']
        )

        st.session_state['battle_logs'].extend(logs)
        st.session_state['action_idx'] += 1

    # Если действия кончились
    if st.session_state['action_idx'] >= len(actions):
        step_finish()


def step_finish():
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']
    sys_clash = ClashSystem()

    end_logs = sys_clash.finalize_turn(p1, p2)
    st.session_state['battle_logs'].extend(end_logs)

    finish_round_logic()  # Вызываем общую логику конца раунда


# Старая функция "Auto Run", переименованная для ясности
def execute_combat_auto():
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']
    sys_clash = ClashSystem()

    with capture_output() as captured:
        logs = sys_clash.resolve_turn(p1, p2)

    st.session_state['battle_logs'] = logs
    st.session_state['script_logs'] = captured.getvalue()

    finish_round_logic()


def finish_round_logic():
    """Общая логика завершения раунда (хил, стаггер, кулдауны)"""
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']

    msg = []
    if p1.active_slots and p1.active_slots[0].get('stunned'):
        p1.current_stagger = p1.max_stagger
        msg.append(f"✨ {p1.name} recovered!")

    if p2.active_slots and p2.active_slots[0].get('stunned'):
        p2.current_stagger = p2.max_stagger
        msg.append(f"✨ {p2.name} recovered!")

    st.session_state['turn_message'] = " ".join(msg) if msg else "Round Complete."

    # Events & Cooldowns
    def trigger_end(unit, prefix):
        logs = []
        for pid in unit.passives:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_round_end(unit, lambda m: logs.append(m))
        for pid in unit.talents:
            if pid in TALENT_REGISTRY: TALENT_REGISTRY[pid].on_round_end(unit, lambda m: logs.append(m))

        logs.extend(StatusManager.process_turn_end(unit))
        unit.tick_cooldowns()

        if logs:
            st.session_state['battle_logs'].append({"round": "End", "details": ", ".join(logs)})

    trigger_end(p1, "P1")
    trigger_end(p2, "P2")

    p1.active_slots = []
    p2.active_slots = []

    st.session_state['phase'] = 'roll'
    st.session_state['turn_phase'] = 'done'  # Сброс


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


# ui/simulator.py

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

def sync_state_from_widgets(unit: Unit, key_prefix: str):
    for i, slot in enumerate(unit.active_slots):
        # Если слот оглушен, виджетов нет, пропускаем
        if slot.get('stunned'): continue

        lib_key = f"{key_prefix}_lib_{i}"
        if lib_key in st.session_state:
            slot['card'] = st.session_state[lib_key]
        tgt_key = f"{key_prefix}_tgt_{i}"
        if tgt_key in st.session_state:
            slot['target_slot'] = st.session_state[tgt_key]
        aggro_key = f"{key_prefix}_aggro_{i}"
        if aggro_key in st.session_state:
            slot['is_aggro'] = st.session_state[aggro_key]


def precalculate_interactions(p1: Unit, p2: Unit):
    ClashSystem.calculate_redirections(p1, p2)
    ClashSystem.calculate_redirections(p2, p1)

    def _calc_ui(me, enemy):
        for i, my_slot in enumerate(me.active_slots):
            # Если оглушен - статус простой
            if my_slot.get('stunned'):
                my_slot['ui_status'] = {"text": "😵 STAGGERED", "icon": "❌", "color": "gray"}
                continue

            target_idx = my_slot.get('target_slot', -1)
            status = {"text": "⛔ NO TARGET", "icon": "⛔", "color": "gray"}

            if target_idx != -1 and target_idx < len(enemy.active_slots):
                enemy_slot = enemy.active_slots[target_idx]

                # Если враг целится в нас -> CLASH
                if enemy_slot.get('target_slot') == i:
                    status = {"text": f"CLASH S{target_idx + 1}", "icon": "⚔️", "color": "red"}
                else:
                    status = {"text": f"ATK S{target_idx + 1}", "icon": "🏹", "color": "orange"}

            my_slot['ui_status'] = status

    _calc_ui(p1, p2)
    _calc_ui(p2, p1)


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


# ui/simulator.py

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