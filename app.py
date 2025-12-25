import streamlit as st
from core.models import Unit, Card, Dice, DiceType, Resistances
from logic.clash import ClashSystem

st.set_page_config(page_title="LoR Advanced Calc", layout="wide")
st.title("⚔️ Combat System: Stagger & Resistances")


# --- Helpers ---
def render_resist_inputs(prefix):
    c1, c2, c3 = st.columns(3)
    s = c1.number_input("Slash Res", 0.1, 2.0, 1.0, 0.5, key=f"{prefix}_s")
    p = c2.number_input("Pierce Res", 0.1, 2.0, 1.0, 0.5, key=f"{prefix}_p")
    b = c3.number_input("Blunt Res", 0.1, 2.0, 1.0, 0.5, key=f"{prefix}_b")
    return Resistances(s, p, b)


def render_card_builder(key_prefix, default_name):
    with st.container(border=True):
        st.subheader(default_name)
        count = st.slider(f"Dice Count", 1, 5, 3, key=f"{key_prefix}_cnt")
        configs = []
        for i in range(count):
            c1, c2, c3 = st.columns([1.5, 1, 1])
            d_type = c1.selectbox("Type", [t.value for t in DiceType], key=f"{key_prefix}_t_{i}")
            d_min = c2.number_input("Min", 1, 20, 3, key=f"{key_prefix}_min_{i}", label_visibility="collapsed")
            d_max = c3.number_input("Max", 1, 20, 7, key=f"{key_prefix}_max_{i}", label_visibility="collapsed")
            configs.append(Dice(d_min, d_max, DiceType(d_type)))
        return Card(default_name, 0, configs)


# --- Layout ---
col_atk, col_mid, col_def = st.columns([1, 0.2, 1])

with col_atk:
    st.info("🟦 Attacker (Roland)")
    card_a = render_card_builder("atk", "Furioso")
    # Для простоты атакующий имеет стандартные резисты

with col_def:
    st.error("🟥 Defender (Argalia)")
    card_b = render_card_builder("def", "Blue Reverberation")

    st.caption("HP Resistances")
    res_hp = render_resist_inputs("hp")
    st.caption("Stagger Resistances")
    res_stagger = render_resist_inputs("stg")

    start_hp = st.number_input("Start HP", 50, 200, 100)
    start_stg = st.number_input("Start Stagger", 20, 100, 50)

with col_mid:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    btn_clash = st.button("FIGHT", type="primary")

if btn_clash:
    # Setup Units
    # Атакующему карту дали
    u_atk = Unit("Roland", current_card=card_a)

    # ИСПРАВЛЕНИЕ: Добавляем current_card=card_b в аргументы
    u_def = Unit("Argalia",
                 max_hp=start_hp, current_hp=start_hp,
                 max_stagger=start_stg, current_stagger=start_stg,
                 current_card=card_b)  # <--- ВОТ ЭТОГО НЕ ХВАТАЛО

    # Применяем резисты из UI
    u_def.hp_resists = res_hp
    u_def.stagger_resists = res_stagger

    # Process
    sys = ClashSystem()
    # Теперь resolve_card_clash не упадет, так как у u_def есть карта
    logs = sys.resolve_card_clash(u_atk, u_def)

    # Output
    st.divider()

    # Status Bar
    c1, c2 = st.columns(2)
    c1.metric("Defender HP", f"{u_def.current_hp}/{u_def.max_hp}", delta=u_def.current_hp - start_hp)
    c2.metric("Defender Stagger", f"{u_def.current_stagger}/{u_def.max_stagger}",
              delta=u_def.current_stagger - start_stg)

    if u_def.is_staggered():
        st.error("⚠️ TARGET IS STAGGERED!")

    st.subheader("Combat Log")
    for log in logs:
        st.markdown(f"**{log['round']}**: {log['rolls']} -> {log['details']}")