import streamlit as st
from core.models import Unit, Card, Dice, DiceType, Resistances
from core.library import Library
from logic.clash import ClashSystem

st.set_page_config(page_title="LoR Combat Sim", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 18px; }
    .stProgress { margin-top: -10px; margin-bottom: 10px; }
    /* Убираем лишние отступы у кнопок */
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTS ---
TYPE_ICONS = {DiceType.SLASH: "🗡️", DiceType.PIERCE: "🏹", DiceType.BLUNT: "🔨", DiceType.BLOCK: "🛡️",
              DiceType.EVADE: "💨"}
TYPE_COLORS = {DiceType.SLASH: "red", DiceType.PIERCE: "green", DiceType.BLUNT: "orange", DiceType.BLOCK: "blue",
               DiceType.EVADE: "gray"}

# --- STATE INIT ---
if 'attacker' not in st.session_state:
    st.session_state['attacker'] = Unit("Roland", max_hp=100, current_hp=100)
if 'defender' not in st.session_state:
    st.session_state['defender'] = Unit("Argalia", max_hp=120, current_hp=120)
if 'battle_logs' not in st.session_state:
    st.session_state['battle_logs'] = []
if 'turn_message' not in st.session_state:
    st.session_state['turn_message'] = ""


# --- LOGIC CALLBACK (МАТЕМАТИКА) ---
def run_combat():
    """
    Эта функция выполняется ДО рендера страницы.
    Она меняет данные в session_state, поэтому при отрисовке
    пользователь сразу видит новые HP без скачков.
    """
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']

    # 1. Логика Стаггера (До боя)
    p1_stag = p1.is_staggered()
    p2_stag = p2.is_staggered()

    # Сохраняем реальные карты, чтобы потом вернуть (если нужно)
    # Но для расчета подменяем на "Stunned", если оглушен
    real_card_1 = p1.current_card
    real_card_2 = p2.current_card

    if p1_stag: p1.current_card = Card("Stun", 0, [])
    if p2_stag: p2.current_card = Card("Stun", 0, [])

    # 2. Расчет
    sys = ClashSystem()
    logs = sys.resolve_card_clash(p1, p2)
    st.session_state['battle_logs'] = logs  # Сохраняем логи для отрисовки

    # 3. Логика Стаггера (После боя - восстановление)
    msg = []
    if p1_stag:
        p1.current_stagger = p1.max_stagger
        msg.append(f"{p1.name} recovered!")
    if p2_stag:
        p2.current_stagger = p2.max_stagger
        msg.append(f"{p2.name} recovered!")

    st.session_state['turn_message'] = " ".join(msg)

    # Возвращаем карты (для UI), хотя бой уже прошел
    if p1_stag: p1.current_card = real_card_1
    if p2_stag: p2.current_card = real_card_2


def reset_game():
    del st.session_state['attacker']
    del st.session_state['defender']
    st.session_state['battle_logs'] = []
    st.session_state['turn_message'] = ""


# --- UI COMPONENTS ---

def render_unit_stats(unit):
    # Отрисовка без st.empty, просто поток элементов
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

    # Важно: Выбор карты происходит здесь, но он сохраняется в unit.current_card
    # Мы не пересоздаем объект Unit, мы меняем его поле.

    if mode == "📚 Library":
        all_cards = Library.get_all_names()
        # Индекс 0 по умолчанию, или сохраняем прошлый выбор через key
        card_name = st.selectbox("Preset", all_cards, key=f"{key_prefix}_lib")
        selected_card = Library.get_card(card_name)
        if selected_card.description: st.caption(f"📝 {selected_card.description}")
    else:
        with st.container(border=True):
            c_name = st.text_input("Name", "My Card", key=f"{key_prefix}_custom_name")
            num_dice = st.slider("Dice", 1, 4, 2, key=f"{key_prefix}_cnt")
            custom_dice = []
            for i in range(num_dice):
                c1, c2, c3 = st.columns([1.2, 1, 1])
                dtype = c1.selectbox("T", [t.value for t in DiceType], key=f"{key_prefix}_d_{i}_t",
                                     label_visibility="collapsed")
                dmin = c2.number_input("Min", 1, 20, 3, key=f"{key_prefix}_d_{i}_min", label_visibility="collapsed")
                dmax = c3.number_input("Max", 1, 20, 7, key=f"{key_prefix}_d_{i}_max", label_visibility="collapsed")
                custom_dice.append(Dice(dmin, dmax, DiceType(dtype)))
            selected_card = Card(c_name, 0, custom_dice)

    if not unit.is_staggered():
        unit.current_card = selected_card

    return unit.current_card  # Возвращаем для визуала


def render_card_visual(card, is_staggered=False):
    with st.container(border=True):
        if is_staggered:
            st.error("😵 Staggered")
            st.caption("Cannot act this turn")
            return
        # Защита от None
        if not card:
            st.warning("No card selected")
            return

        st.markdown(f"**{card.name}**")
        cols = st.columns(len(card.dice_list))
        for i, dice in enumerate(card.dice_list):
            color = TYPE_COLORS[dice.dtype]
            with cols[i]:
                st.markdown(f":{color}[{TYPE_ICONS[dice.dtype]}]")
                st.write(f"**{dice.min_val}-{dice.max_val}**")
                if dice.effects:
                    for eff in dice.effects: st.caption(f"*{eff}*")


# --- MAIN PAGE LAYOUT ---
st.title("⚔️ LoR Sim: Smooth Edition")
with st.sidebar:
    st.button("🔄 Reset Battle", on_click=reset_game)

# 1. Получаем ссылки на объекты (они уже обновлены если была нажата кнопка)
p1 = st.session_state['attacker']
p2 = st.session_state['defender']

col_left, col_right = st.columns(2)

# === ЛЕВАЯ КОЛОНКА ===
with col_left:
    render_unit_stats(p1)  # Рисуем УЖЕ обновленные статы
    render_resist_inputs(p1, "p1")
    vis_card_1 = card_selector_ui(p1, "p1")
    render_card_visual(vis_card_1, p1.is_staggered())

# === ПРАВАЯ КОЛОНКА ===
with col_right:
    render_unit_stats(p2)  # Рисуем УЖЕ обновленные статы
    render_resist_inputs(p2, "p2")
    vis_card_2 = card_selector_ui(p2, "p2")
    render_card_visual(vis_card_2, p2.is_staggered())

# === ЦЕНТРАЛЬНАЯ КНОПКА (ACTION) ===
st.divider()
c_mid = st.columns([1, 2, 1])[1]
with c_mid:
    btn_label = "COMBAT START"
    if p1.is_staggered() or p2.is_staggered():
        btn_label = "ONE-SIDED ATTACK (Finish Stagger)"

    # ГЛАВНОЕ: on_click вызывает run_combat ДО перезагрузки страницы
    st.button(btn_label, type="primary", on_click=run_combat)

# === ЛОГИ (Рисуются из session_state) ===
if st.session_state['turn_message']:
    st.success(st.session_state['turn_message'])

if st.session_state['battle_logs']:
    for log in st.session_state['battle_logs']:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 4])
            c1.write(f"**R{log['round']}**: {log['rolls']}")
            det = log['details']
            if "Win" in det:
                c3.write(f"⚔️ {det}")
            elif "One-Sided" in det:
                c3.error(det)
            elif "Stagger" in det:
                c3.warning(det)
            else:
                c3.info(det)