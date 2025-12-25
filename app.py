import streamlit as st
from core.models import Unit
from ui.styles import apply_styles
from ui.simulator import render_simulator_page
from ui.editor import render_editor_page

# Применяем CSS и конфиг
apply_styles()

# --- STATE INIT ---
if 'attacker' not in st.session_state:
    st.session_state['attacker'] = Unit("Roland", max_hp=100, current_hp=100)
if 'defender' not in st.session_state:
    st.session_state['defender'] = Unit("Argalia", max_hp=120, current_hp=120)
if 'battle_logs' not in st.session_state: st.session_state['battle_logs'] = []
if 'script_logs' not in st.session_state: st.session_state['script_logs'] = ""
if 'turn_message' not in st.session_state: st.session_state['turn_message'] = ""

# --- NAVIGATION ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["⚔️ Simulator", "🛠️ Card Editor"])

if "Simulator" in page:
    render_simulator_page()
else:
    render_editor_page()