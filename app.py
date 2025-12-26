# app.py
import streamlit as st
from core.models import Unit  # models.py теперь просто импортирует Unit из core/unit.py
from core.unit_library import UnitLibrary
from ui.styles import apply_styles
from ui.simulator import render_simulator_page
from ui.editor import render_editor_page
from ui.profile import render_profile_page

# Применяем CSS и конфиг
apply_styles()

# --- INIT ROSTER (ЗАГРУЗКА ИЗ ФАЙЛОВ) ---
if 'roster' not in st.session_state:
    loaded_roster = UnitLibrary.load_all()

    # Если папка пуста, создаем тестового Роланда
    if not loaded_roster:
        roland = Unit("Roland")
        # Настраиваем статы
        roland.attributes["endurance"] = 5
        roland.attributes["strength"] = 5
        roland.base_hp = 75  # База 20 + 75 = 95 (+ выносливость)

        # ВАЖНО: Пересчитываем статы и лечим его полностью при создании
        roland.recalculate_stats()
        roland.current_hp = roland.max_hp  # <--- Вот это фиксит проблему "20 хп"
        roland.current_sp = roland.max_sp

        UnitLibrary.save_unit(roland)
        loaded_roster = UnitLibrary.load_all()

    st.session_state['roster'] = loaded_roster

# --- SYNC SIMULATOR WITH ROSTER ---
# Проверяем валидность ключей (вдруг файл удалили, а сессия осталась)
roster_keys = list(st.session_state['roster'].keys())
if not roster_keys:
    st.error("Roster is empty! Please create a character in Profile tab.")
    st.stop()

# Дефолтный выбор бойцов
if 'attacker_name' not in st.session_state: st.session_state['attacker_name'] = roster_keys[0]
if 'defender_name' not in st.session_state: st.session_state['defender_name'] = roster_keys[-1] if len(
    roster_keys) > 1 else roster_keys[0]

# Получаем объекты по именам
p1 = st.session_state['roster'].get(st.session_state['attacker_name'])
p2 = st.session_state['roster'].get(st.session_state['defender_name'])

# Пишем их в стейт для симулятора (он ожидает объекты 'attacker' и 'defender')
st.session_state['attacker'] = p1
st.session_state['defender'] = p2

if 'battle_logs' not in st.session_state: st.session_state['battle_logs'] = []
if 'script_logs' not in st.session_state: st.session_state['script_logs'] = ""
if 'turn_message' not in st.session_state: st.session_state['turn_message'] = ""

# --- NAVIGATION ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["⚔️ Simulator", "👤 Profile", "🛠️ Card Editor"])

if "Simulator" in page:
    st.sidebar.divider()
    st.sidebar.markdown("**Fight Setup**")

    # Выбираем ИМЕНА из списка
    a_name = st.sidebar.selectbox("Attacker (Left)", roster_keys,
                                  index=roster_keys.index(st.session_state['attacker_name']) if st.session_state[
                                                                                                    'attacker_name'] in roster_keys else 0)
    d_name = st.sidebar.selectbox("Defender (Right)", roster_keys,
                                  index=roster_keys.index(st.session_state['defender_name']) if st.session_state[
                                                                                                    'defender_name'] in roster_keys else 0)

    # Сохраняем выбор
    st.session_state['attacker_name'] = a_name
    st.session_state['defender_name'] = d_name
    # Обновляем объекты
    st.session_state['attacker'] = st.session_state['roster'][a_name]
    st.session_state['defender'] = st.session_state['roster'][d_name]

    render_simulator_page()

elif "Profile" in page:
    render_profile_page()

else:
    render_editor_page()