import streamlit as st
import sys
from io import StringIO
from contextlib import contextmanager
import uuid

from core.models import Unit, Card, Dice, DiceType, Resistances
from core.library import Library
from logic.clash import ClashSystem
from logic.statuses import StatusManager

st.set_page_config(page_title="LoR Engine", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 18px; }
    .stProgress { margin-top: -10px; margin-bottom: 10px; }
    .stButton button { width: 100%; }
    /* Стиль для логов скриптов */
    .script-log { font-family: monospace; color: #00ff41; background-color: #0d1117; padding: 5px; border-radius: 5px; margin-bottom: 5px; font-size: 0.8em; }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTS ---
TYPE_ICONS = {DiceType.SLASH: "🗡️", DiceType.PIERCE: "🏹", DiceType.BLUNT: "🔨", DiceType.BLOCK: "🛡️",
              DiceType.EVADE: "💨"}
TYPE_COLORS = {DiceType.SLASH: "red", DiceType.PIERCE: "green", DiceType.BLUNT: "orange", DiceType.BLOCK: "blue",
               DiceType.EVADE: "gray"}


# --- UTILS: CAPTURE PRINT ---
@contextmanager
def capture_output():
    """Перехватывает print() из скриптов"""
    new_out = StringIO()
    old_out = sys.stdout
    try:
        sys.stdout = new_out
        yield new_out
    finally:
        sys.stdout = old_out


# --- STATE INIT ---
if 'attacker' not in st.session_state:
    st.session_state['attacker'] = Unit("Roland", max_hp=100, current_hp=100)
if 'defender' not in st.session_state:
    st.session_state['defender'] = Unit("Argalia", max_hp=120, current_hp=120)
if 'battle_logs' not in st.session_state: st.session_state['battle_logs'] = []
if 'script_logs' not in st.session_state: st.session_state['script_logs'] = ""
if 'turn_message' not in st.session_state: st.session_state['turn_message'] = ""


# --- LOGIC CALLBACK ---
def run_combat():
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']

    p1_stag = p1.is_staggered()
    p2_stag = p2.is_staggered()

    real_card_1 = p1.current_card
    real_card_2 = p2.current_card

    if p1_stag: p1.current_card = Card(name="Stunned", dice_list=[])
    if p2_stag: p2.current_card = Card(name="Stunned", dice_list=[])

    sys_clash = ClashSystem()

    with capture_output() as captured:
        logs = sys_clash.resolve_card_clash(p1, p2)

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

    end_turn_logs_p1 = StatusManager.process_turn_end(p1)
    end_turn_logs_p2 = StatusManager.process_turn_end(p2)

    # Добавить эти логи в общий лог
    if end_turn_logs_p1: st.session_state['battle_logs'].append(
        {"round": "End", "rolls": "P1 Statuses", "details": ", ".join(end_turn_logs_p1)})
    if end_turn_logs_p2: st.session_state['battle_logs'].append(
        {"round": "End", "rolls": "P2 Statuses", "details": ", ".join(end_turn_logs_p2)})


def reset_game():
    del st.session_state['attacker']
    del st.session_state['defender']
    st.session_state['battle_logs'] = []
    st.session_state['script_logs'] = ""
    st.session_state['turn_message'] = ""


# --- UI COMPONENTS (HELPER FUNCTIONS) ---

def render_unit_stats(unit):
    # Определяем цвет иконки (для красоты заголовка)
    icon = '🟦' if 'Roland' in unit.name else '🟥'
    st.markdown(f"### {icon} {unit.name}")

    # --- 1. HP Bar ---
    # Защита от деления на 0
    max_hp = unit.max_hp if unit.max_hp > 0 else 1
    hp_pct = max(0.0, min(1.0, unit.current_hp / max_hp))
    st.progress(hp_pct, text=f"HP: {unit.current_hp}/{unit.max_hp}")

    # --- 2. Stagger Bar ---
    max_stg = unit.max_stagger if unit.max_stagger > 0 else 1
    stg_pct = max(0.0, min(1.0, unit.current_stagger / max_stg))
    st.progress(stg_pct, text=f"Stagger: {unit.current_stagger}/{unit.max_stagger}")

    # --- 3. Sanity (SP) Bar ---
    # Диапазон SP: от -Max до +Max. Всего делений = Max * 2.
    # Пример: от -45 до +45 (размер 90).
    # 0 SP должно быть посередине (0.5).

    sp_limit = unit.max_sp  # Например, 45
    total_range = sp_limit * 2  # 90
    if total_range == 0: total_range = 1

    # Сдвигаем текущее значение, чтобы -45 стало 0
    # Пример: current = -45 -> shifted = 0. current = 0 -> shifted = 45.
    current_shifted = unit.current_sp + sp_limit

    sp_pct = current_shifted / total_range
    # Обрезаем границы (clamp), чтобы не вылетело за 0.0-1.0
    sp_pct = max(0.0, min(1.0, sp_pct))

    # Добавляем эмодзи настроения в текст
    mood = "😐"
    if unit.current_sp >= 20:
        mood = "🙂"
    elif unit.current_sp >= 40:
        mood = "😄"
    elif unit.current_sp <= -20:
        mood = "😨"
    elif unit.current_sp <= -40:
        mood = "😱"

    st.progress(sp_pct, text=f"Sanity: {unit.current_sp}/{unit.max_sp} {mood}")

    # --- 4. Statuses ---
    if unit.statuses:
        st.markdown("---")
        # Отображаем статусы компактной сеткой
        cols = st.columns(4)
        idx = 0
        for name, val in unit.statuses.items():
            with cols[idx % 4]:
                st.metric(label=name.capitalize(), value=val)
            idx += 1


def render_resist_inputs(unit, key_prefix):
    with st.expander(f"🛡️ Resistances"):
        c1, c2 = st.columns(2)
        with c1:
            h_s = st.number_input("Sl", 0.1, 2.0, unit.hp_resists.slash, 0.1, key=f"{key_prefix}_hs")
            h_p = st.number_input("Pi", 0.1, 2.0, unit.hp_resists.pierce, 0.1, key=f"{key_prefix}_hp")
            h_b = st.number_input("Bl", 0.1, 2.0, unit.hp_resists.blunt, 0.1, key=f"{key_prefix}_hb")
            unit.hp_resists = Resistances(h_s, h_p, h_b)
        with c2:
            s_s = st.number_input("Sl", 0.1, 2.0, unit.stagger_resists.slash, 0.1, key=f"{key_prefix}_ss")
            s_p = st.number_input("Pi", 0.1, 2.0, unit.stagger_resists.pierce, 0.1, key=f"{key_prefix}_sp")
            s_b = st.number_input("Bl", 0.1, 2.0, unit.stagger_resists.blunt, 0.1, key=f"{key_prefix}_sb")
            unit.stagger_resists = Resistances(s_s, s_p, s_b)


def card_selector_ui(unit, key_prefix):
    mode = st.radio("Src", ["📚 Library", "🛠️ Custom"], key=f"{key_prefix}_mode", horizontal=True,
                    label_visibility="collapsed")

    if mode == "📚 Library":
        # Получаем все карты (объекты)
        all_cards_objs = Library.get_all_cards()
        if not all_cards_objs:
            st.error("Library empty!")
            return None

        # Создаем карту имен для SelectBox: "Название (ID)" -> Объект
        # Это решает проблему дубликатов имен
        options_map = {f"{c.name} ({c.id})": c for c in all_cards_objs}

        selected_key = st.selectbox("Preset", list(options_map.keys()), key=f"{key_prefix}_lib")
        selected_card = options_map[selected_key]

        if selected_card.description:
            st.caption(f"📝 {selected_card.description}")

    else:
        with st.container(border=True):
            c_name = st.text_input("Name", "My Card", key=f"{key_prefix}_custom_name")
            num_dice = st.slider("Dice", 1, 4, 2, key=f"{key_prefix}_cnt")
            custom_dice = []
            for i in range(num_dice):
                c1, c2, c3 = st.columns([1.5, 1, 1])
                dtype_str = c1.selectbox("T", [t.name for t in DiceType], key=f"{key_prefix}_d_{i}_t",
                                         label_visibility="collapsed")
                dmin = c2.number_input("Min", 1, 50, 4, key=f"{key_prefix}_d_{i}_min", label_visibility="collapsed")
                dmax = c3.number_input("Max", 1, 50, 8, key=f"{key_prefix}_d_{i}_max", label_visibility="collapsed")
                custom_dice.append(Dice(dmin, dmax, DiceType[dtype_str]))
                # Передаем список кубиков в правильный аргумент
                selected_card = Card(name=c_name, dice_list=custom_dice, description="Custom Card")

    if not unit.is_staggered():
        unit.current_card = selected_card

    return unit.current_card


def render_card_visual(card, is_staggered=False):
    with st.container(border=True):
        if is_staggered:
            st.error("😵 STAGGERED")
            return
        if not card:
            st.warning("No card selected")
            return

        type_icon = "🏹" if card.card_type == "ranged" else "⚔️"
        st.markdown(f"**{card.name}** ({type_icon}")

        if card.scripts:
            with st.expander("Effects", expanded=False):
                for trig, scripts in card.scripts.items():
                    for s in scripts: st.markdown(f"- `{s['script_id']}`")

        cols = st.columns(len(card.dice_list)) if card.dice_list else [st]
        for i, dice in enumerate(card.dice_list):
            with cols[i]:
                color = TYPE_COLORS.get(dice.dtype, "black")
                icon = TYPE_ICONS.get(dice.dtype, "?")
                st.markdown(f":{color}[{icon} **{dice.min_val}-{dice.max_val}**]")
                if dice.scripts:
                    for trig, effs in dice.scripts.items():
                        for e in effs: st.caption(f"*{e.get('script_id')}*")


# ==========================================
# PAGE 1: SIMULATOR (FULL VERSION)
# ==========================================
def render_simulator():
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

    # КНОПКА БОЯ
    btn_col = st.columns([1, 2, 1])[1]
    with btn_col:
        label = "🔥 CLASH START 🔥"
        if p1.is_staggered() or p2.is_staggered():
            label = "⚔️ ONE-SIDED ATTACK"
        st.button(label, type="primary", on_click=run_combat, use_container_width=True)

    # ЛОГИ
    st.subheader("📜 Battle Report")

    if st.session_state['turn_message']:
        st.success(st.session_state['turn_message'])

    if st.session_state['script_logs']:
        with st.expander("🛠️ Script & Effect Logs (Debug)", expanded=True):
            st.markdown(f"<div class='script-log'>{st.session_state['script_logs'].replace(chr(10), '<br>')}</div>",
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
                else:
                    c3.info(det)


# ==========================================
# PAGE 2: CARD EDITOR
# ==========================================
def render_editor():
    st.header("🛠️ Card Creator (Status Update)")
    st.info("Создайте карту и добавьте эффекты (Кровотечение, Паралич и т.д.)")

    # === [ИСПРАВЛЕНИЕ] Слайдер вынесен из формы, чтобы обновлять UI мгновенно ===
    st.subheader("Настройка Кубиков")
    num_dice = st.slider("Количество кубиков", 1, 4, 3)

    # Теперь открываем форму
    with st.form("new_card_form"):
        c1, c2 = st.columns([3, 1])
        name = c1.text_input("Название карты", "Frenzy")
        tier = c2.selectbox("Уровень (Tier)", [1, 2, 3], index=0)

        c3, c4 = st.columns(2)
        ctype = c3.selectbox("Тип", ["melee", "ranged"])
        desc = c4.text_area("Описание", "On Hit: Inflict 1 Bleed")

        st.divider()

        dice_data = []
        available_statuses = ["None", "bleed", "paralysis", "burn", "strength", "weakness", "haste", "bind"]

        # Цикл теперь использует значение снаружи формы, которое обновляется сразу
        for i in range(num_dice):
            with st.container(border=True):
                st.markdown(f"**🎲 Кубик {i + 1}**")

                dc1, dc2, dc3, dc4 = st.columns([1.5, 1, 1, 2])
                d_type_str = dc1.selectbox(f"Тип", ["Slash", "Pierce", "Blunt", "Block", "Evade"], key=f"d_type_{i}")
                d_min = dc2.number_input(f"Min", 1, 50, 2, key=f"d_min_{i}")
                d_max = dc3.number_input(f"Max", 1, 50, 4, key=f"d_max_{i}")

                st.markdown("👇 **Эффект (Script)**")
                ec1, ec2, ec3 = st.columns([2, 1, 1.5])

                effect_name = ec1.selectbox("Наложить статус", available_statuses, key=f"eff_name_{i}")
                effect_amt = ec2.number_input("Сила", 1, 10, 1, key=f"eff_amt_{i}")
                trigger = ec3.selectbox("Триггер", ["on_hit", "on_clash_win", "on_use"], key=f"trig_{i}")

                # Собираем данные (логика та же)
                scripts_dict = {}
                if effect_name != "None":
                    script_payload = {
                        "script_id": "apply_status",
                        "params": {
                            "status": effect_name,
                            "stack": int(effect_amt),
                            "target": "target"
                        }
                    }
                    scripts_dict[trigger] = [script_payload]

                type_enum = DiceType.SLASH
                if d_type_str == "Pierce":
                    type_enum = DiceType.PIERCE
                elif d_type_str == "Blunt":
                    type_enum = DiceType.BLUNT
                elif d_type_str == "Block":
                    type_enum = DiceType.BLOCK
                elif d_type_str == "Evade":
                    type_enum = DiceType.EVADE

                dice_obj = Dice(d_min, d_max, type_enum)
                dice_obj.scripts = scripts_dict
                dice_data.append(dice_obj)

        st.divider()
        auto_id = name.lower().replace(" ", "_") + "_" + str(uuid.uuid4())[:4]
        card_id = st.text_input("Unique ID", auto_id)

        submitted = st.form_submit_button("💾 Сохранить в Библиотеку", type="primary")

        if submitted:
            new_card = Card(
                id=card_id,
                name=name,
                tier=tier,
                card_type=ctype,
                description=desc,
                dice_list=dice_data
            )
            Library.save_card(new_card, filename="custom_cards.json")
            st.success(f"Карта '{name}' ({len(dice_data)} кубиков) сохранена!")
            st.balloons()


# ==========================================
# MAIN APP NAVIGATION
# ==========================================
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["⚔️ Simulator", "🛠️ Card Editor"])

if "Simulator" in page:
    render_simulator()
else:
    render_editor()