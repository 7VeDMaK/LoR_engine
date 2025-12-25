import streamlit as st
import sys
from io import StringIO
from contextlib import contextmanager
import uuid

from core.models import Unit, Card, Dice, DiceType, Resistances
from core.library import Library
from logic.clash import ClashSystem

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

    if p1_stag: p1.current_card = Card("Stunned", 0, [])
    if p2_stag: p2.current_card = Card("Stunned", 0, [])

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


def reset_game():
    del st.session_state['attacker']
    del st.session_state['defender']
    st.session_state['battle_logs'] = []
    st.session_state['script_logs'] = ""
    st.session_state['turn_message'] = ""


# --- UI COMPONENTS (HELPER FUNCTIONS) ---

def render_unit_stats(unit):
    st.markdown(f"### {'🟦' if 'Roland' in unit.name else '🟥'} {unit.name}")
    hp_pct = max(0, unit.current_hp / unit.max_hp)
    st.progress(hp_pct, text=f"HP: {unit.current_hp}/{unit.max_hp}")
    stg_pct = max(0, unit.current_stagger / unit.max_stagger)
    st.progress(stg_pct, text=f"Stagger: {unit.current_stagger}/{unit.max_stagger}")


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
            selected_card = Card(c_name, 0, custom_dice)

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
    st.header("🛠️ Card Creator")
    st.info("Create a new card and add it to the Library permanently.")

    with st.form("new_card_form"):
        # ИЗМЕНЕНИЕ: Убрали колонку Cost. Теперь только Имя и Тир.
        c1, c2 = st.columns([3, 1])
        name = c1.text_input("Card Name", "New Attack")
        tier = c2.selectbox("Tier", [1, 2, 3], index=0)

        c3, c4 = st.columns(2)
        ctype = c3.selectbox("Type", ["melee", "ranged"])
        desc = c4.text_area("Description", "On Use: ...")

        st.subheader("Dice Configuration")
        num_dice = st.slider("Dice Count", 1, 5, 2)

        dice_data = []
        for i in range(num_dice):
            st.markdown(f"**Die {i + 1}**")
            dc1, dc2, dc3 = st.columns([1, 1, 1])
            d_type = dc1.selectbox(f"Type", ["slash", "pierce", "blunt", "block", "evade"], key=f"ed_{i}")
            d_min = dc2.number_input(f"Min", 1, 50, 3, key=f"emin_{i}")
            d_max = dc3.number_input(f"Max", 1, 50, 7, key=f"emax_{i}")

            type_enum = DiceType.SLASH
            if d_type == "pierce":
                type_enum = DiceType.PIERCE
            elif d_type == "blunt":
                type_enum = DiceType.BLUNT
            elif d_type == "block":
                type_enum = DiceType.BLOCK
            elif d_type == "evade":
                type_enum = DiceType.EVADE

            dice_data.append(Dice(d_min, d_max, type_enum))

        st.divider()
        auto_id = name.lower().replace(" ", "_") + "_" + str(uuid.uuid4())[:4]
        card_id = st.text_input("Unique ID", auto_id)

        submitted = st.form_submit_button("💾 Save to Library", type="primary")

        if submitted:
            # ИЗМЕНЕНИЕ: Создаем карту без cost
            new_card = Card(
                id=card_id,
                name=name,
                # Cost удален
                tier=tier,
                card_type=ctype,
                description=desc,
                dice_list=dice_data
            )

            Library.save_card(new_card, filename="custom_cards.json")

            st.success(f"Card '{name}' successfully saved to 'custom_cards.json'!")
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