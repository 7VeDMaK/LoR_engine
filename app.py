import streamlit as st
from core.models import Unit, Card, Dice, DiceType, Resistances
from logic.clash import ClashSystem

st.set_page_config(page_title="LoR Combat Sim", layout="wide")

# --- CSS STYLES ---
st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 18px; }
    .dice-box { border: 1px solid #555; border-radius: 5px; padding: 10px; text-align: center; background: #262730; }
    .st-emotion-cache-16idsys p { font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

# --- CONSTANTS ---
TYPE_ICONS = {DiceType.SLASH: "🗡️", DiceType.PIERCE: "🏹", DiceType.BLUNT: "🔨", DiceType.BLOCK: "🛡️",
              DiceType.EVADE: "💨"}
TYPE_COLORS = {DiceType.SLASH: "red", DiceType.PIERCE: "green", DiceType.BLUNT: "orange", DiceType.BLOCK: "blue",
               DiceType.EVADE: "gray"}


# --- PRESETS (Пока не трогаем, как ты просил) ---
def get_card_presets():
    return {
        "Rampage (Буйство)": Card("Rampage", 3, [Dice(2, 4, DiceType.BLUNT), Dice(3, 5, DiceType.PIERCE),
                                                 Dice(3, 5, DiceType.SLASH)]),
        "Iron Defense": Card("Iron Def", 2, [Dice(5, 9, DiceType.BLOCK), Dice(5, 8, DiceType.BLOCK)]),
        "Evade Master": Card("Dodge", 2, [Dice(6, 12, DiceType.EVADE), Dice(4, 8, DiceType.SLASH)]),
        "Strong Hit": Card("Heavy", 3, [Dice(5, 10, DiceType.BLUNT)]),
        "Basic Attack": Card("Basic", 1, [Dice(3, 7, DiceType.SLASH), Dice(3, 6, DiceType.PIERCE)])
    }


# --- HELPERS ---
def render_resist_inputs(unit, key_prefix):
    """Рисует инпуты резистов и обновляет юнит"""
    with st.expander(f"🛡️ Resistances & Stats ({unit.name})"):
        c1, c2 = st.columns(2)
        with c1:
            st.caption("HP Resistances")
            h_s = st.number_input("Slash", 0.1, 2.0, unit.hp_resists.slash, 0.1, key=f"{key_prefix}_h_s")
            h_p = st.number_input("Pierce", 0.1, 2.0, unit.hp_resists.pierce, 0.1, key=f"{key_prefix}_h_p")
            h_b = st.number_input("Blunt", 0.1, 2.0, unit.hp_resists.blunt, 0.1, key=f"{key_prefix}_h_b")
            unit.hp_resists = Resistances(h_s, h_p, h_b)
        with c2:
            st.caption("Stagger Resistances")
            s_s = st.number_input("Slash", 0.1, 2.0, unit.stagger_resists.slash, 0.1, key=f"{key_prefix}_s_s")
            s_p = st.number_input("Pierce", 0.1, 2.0, unit.stagger_resists.pierce, 0.1, key=f"{key_prefix}_s_p")
            s_b = st.number_input("Blunt", 0.1, 2.0, unit.stagger_resists.blunt, 0.1, key=f"{key_prefix}_s_b")
            unit.stagger_resists = Resistances(s_s, s_p, s_b)


def render_card_visual(unit_name, card, is_staggered=False):
    with st.container(border=True):
        if is_staggered:
            st.error(f"😵 {unit_name} is Staggered!")
            st.caption("Cannot act this turn. All dice removed.")
            return

        st.subheader(f"🃏 {card.name}")
        cols = st.columns(len(card.dice_list))
        for i, dice in enumerate(card.dice_list):
            color = TYPE_COLORS[dice.dtype]
            with cols[i]:
                st.markdown(f":{color}[**{TYPE_ICONS[dice.dtype]} {dice.dtype.value}**]")
                st.markdown(f"**{dice.min_val} ~ {dice.max_val}**")


# --- INIT STATE ---
if 'attacker' not in st.session_state:
    st.session_state['attacker'] = Unit("Roland", max_hp=100, current_hp=100, max_stagger=50, current_stagger=50)
if 'defender' not in st.session_state:
    st.session_state['defender'] = Unit("Argalia", max_hp=120, current_hp=120, max_stagger=60, current_stagger=60)

p1 = st.session_state['attacker']
p2 = st.session_state['defender']

# --- SIDEBAR CONTROL ---
with st.sidebar:
    st.title("⚙️ Control Panel")
    if st.button("🔄 Full Reset"):
        del st.session_state['attacker']
        del st.session_state['defender']
        st.rerun()

# --- MAIN UI ---
st.title("⚔️ Library of Ruina Simulator")
presets = get_card_presets()
col_left, col_right = st.columns(2)

# === LEFT UNIT ===
with col_left:
    st.markdown(f"### 🟦 {p1.name}")
    # Stats
    st.progress(max(0, p1.current_hp / p1.max_hp), text=f"HP: {p1.current_hp}/{p1.max_hp}")
    st.progress(max(0, p1.current_stagger / p1.max_stagger), text=f"Stagger: {p1.current_stagger}/{p1.max_stagger}")

    # Resistances Input
    render_resist_inputs(p1, "p1")

    # Card Selection
    c1_name = st.selectbox("Select Card", list(presets.keys()), key="p1_sel", disabled=p1.is_staggered())
    p1.current_card = presets[c1_name]

    # Visual
    render_card_visual(p1.name, p1.current_card, is_staggered=p1.is_staggered())

# === RIGHT UNIT ===
with col_right:
    st.markdown(f"### 🟥 {p2.name}")
    # Stats
    st.progress(max(0, p2.current_hp / p2.max_hp), text=f"HP: {p2.current_hp}/{p2.max_hp}")
    st.progress(max(0, p2.current_stagger / p2.max_stagger), text=f"Stagger: {p2.current_stagger}/{p2.max_stagger}")

    # Resistances Input
    render_resist_inputs(p2, "p2")

    # Card Selection
    c2_name = st.selectbox("Select Card", list(presets.keys()), index=1, key="p2_sel", disabled=p2.is_staggered())
    p2.current_card = presets[c2_name]

    # Visual
    render_card_visual(p2.name, p2.current_card, is_staggered=p2.is_staggered())

# === ACTION BUTTON ===
st.divider()
c_btn = st.columns([1, 2, 1])
with c_btn[1]:
    btn_text = "🔥 START CLASH 🔥"
    if p1.is_staggered() or p2.is_staggered():
        btn_text = "⚠️ EXECUTE ONE-SIDED ATTACK (Staggered)"

    fight_btn = st.button(btn_text, type="primary", use_container_width=True)

# === BATTLE LOGIC ===
if fight_btn:
    sys = ClashSystem()

    # 1. Проверяем, кто в стаггере ДО начала боя
    p1_was_staggered = p1.is_staggered()
    p2_was_staggered = p2.is_staggered()

    # 2. Если юнит в стаггере, очищаем его дайсы (он не может атаковать)
    # Важно: мы делаем копию карты или просто очищаем список дайсов в объекте Unit временно
    # В нашей модели Unit ссылается на current_card. Чтобы не сломать пресет, сделаем финт:
    if p1_was_staggered:
        p1.current_card = Card("Stunned", 0, [])  # Пустая карта
    if p2_was_staggered:
        p2.current_card = Card("Stunned", 0, [])

    # 3. Расчет боя
    logs = sys.resolve_card_clash(p1, p2)

    # 4. Вывод логов
    st.subheader("📝 Combat Log")
    for log in logs:
        with st.container(border=True):
            cols = st.columns([2, 1, 4])
            with cols[0]:
                st.markdown(f"**Round {log['round']}**")
                st.caption(log['rolls'])
            with cols[2]:
                det = log['details']
                if "Win" in det:
                    st.write(f"⚔️ {det}")
                elif "One-Sided" in det:
                    st.error(f"🩸 {det}")
                elif "Stagger" in det:
                    st.warning(f"💫 {det}")
                else:
                    st.info(det)

    # 5. ВОССТАНОВЛЕНИЕ СТАГГЕРА (Конец хода)
    # Если юнит БЫЛ в стаггере до этого боя, то после получения урона (One-Sided) он восстанавливается.
    recovered_msg = []

    if p1_was_staggered:
        p1.current_stagger = p1.max_stagger
        recovered_msg.append(f"{p1.name} recovered from Stagger!")

    if p2_was_staggered:
        p2.current_stagger = p2.max_stagger
        recovered_msg.append(f"{p2.name} recovered from Stagger!")

    if recovered_msg:
        st.success(" ".join(recovered_msg))
        # Принудительно обновляем, чтобы показать восстановленную полоску
        # st.rerun() # Можно раскомментировать для мгновенного обновления