# app.py
import streamlit as st
from core.models import Unit
from ui.styles import apply_styles
from ui.simulator import render_simulator_page
from ui.editor import render_editor_page
from ui.profile import render_profile_page  # <-- ИМПОРТ

# Применяем CSS и конфиг
apply_styles()

# --- INIT ROSTER (СПИСОК ПЕРСОНАЖЕЙ) ---
if 'roster' not in st.session_state:
    # Создаем стартовых персонажей с новыми параметрами
    roland = Unit("Roland", max_hp=100, current_hp=100)
    roland.attributes = {"endurance": 22, "psych": 21, "intellect": 6, "agility": 6}
    roland.skills = {"luck": 55, "willpower": 2, "medicine": 3, "speed": 13}

    argalia = Unit("Argalia", max_hp=120, current_hp=120)

    st.session_state['roster'] = {
        "Roland": roland,
        "Argalia": argalia
    }

# --- SYNC SIMULATOR WITH ROSTER ---
# Симулятор по-прежнему ищет attacker/defender.
# Пусть по умолчанию это будут первые два из ростера.
if 'attacker' not in st.session_state:
    st.session_state['attacker'] = st.session_state['roster']["Roland"]
if 'defender' not in st.session_state:
    st.session_state['defender'] = st.session_state['roster']["Argalia"]

if 'battle_logs' not in st.session_state: st.session_state['battle_logs'] = []
if 'script_logs' not in st.session_state: st.session_state['script_logs'] = ""
if 'turn_message' not in st.session_state: st.session_state['turn_message'] = ""

# --- NAVIGATION ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["⚔️ Simulator", "👤 Profile", "🛠️ Card Editor"])

if "Simulator" in page:
    # Небольшой селектор в симуляторе, чтобы менять бойцов из ростера
    st.sidebar.divider()
    st.sidebar.markdown("**Fight Setup**")
    p1_name = st.sidebar.selectbox("Attacker (Left)", list(st.session_state['roster'].keys()), index=0)
    p2_name = st.sidebar.selectbox("Defender (Right)", list(st.session_state['roster'].keys()), index=1)

    # Обновляем ссылки
    st.session_state['attacker'] = st.session_state['roster'][p1_name]
    st.session_state['defender'] = st.session_state['roster'][p2_name]

    render_simulator_page()

elif "Profile" in page:
    render_profile_page()

else:
    render_editor_page()