import streamlit as st
from core.models import DiceType

# --- CONSTANTS ---
TYPE_ICONS = {
    DiceType.SLASH: "🗡️", DiceType.PIERCE: "🏹", DiceType.BLUNT: "🔨",
    DiceType.BLOCK: "🛡️", DiceType.EVADE: "💨"
}
TYPE_COLORS = {
    DiceType.SLASH: "red", DiceType.PIERCE: "green", DiceType.BLUNT: "orange",
    DiceType.BLOCK: "blue", DiceType.EVADE: "gray"
}

def apply_styles():
    st.set_page_config(page_title="LoR Engine", layout="wide")
    st.markdown("""
    <style>
        div[data-testid="stMetricValue"] { font-size: 18px; }
        .stProgress { margin-top: -10px; margin-bottom: 10px; }
        .stButton button { width: 100%; }
        /* Стиль для логов скриптов */
        .script-log { font-family: monospace; color: #00ff41; background-color: #0d1117; padding: 5px; border-radius: 5px; margin-bottom: 5px; font-size: 0.8em; }
    </style>
    """, unsafe_allow_html=True)