import streamlit as st
import random
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Callable, Dict, Optional


# --- 1. ARCHITECTURE CORE (Архитектурное ядро) ---

class DamageType(Enum):
    SLASH = "Slash"
    PIERCE = "Pierce"
    BLUNT = "Blunt"


class TriggerType(Enum):
    ON_ROLL = "OnRoll"
    ON_BEFORE_DAMAGE = "OnBeforeDamage"
    ON_AFTER_DAMAGE = "OnAfterDamage"


@dataclass
class CombatEvent:
    trigger: TriggerType
    source: 'Unit'
    target: 'Unit'
    value: int = 0
    tags: Dict = field(default_factory=dict)


class EventBus:
    """Центральная шина событий. Пассивки подписываются сюда."""

    def __init__(self):
        self.listeners: Dict[TriggerType, List[Callable]] = {t: [] for t in TriggerType}

    def subscribe(self, trigger: TriggerType, callback: Callable):
        self.listeners[trigger].append(callback)

    def emit(self, event: CombatEvent) -> int:
        """Публикует событие. Возвращает модифицированное значение."""
        current_val = event.value
        log_msg = []

        for callback in self.listeners[event.trigger]:
            # Пассивки могут менять значение в событии
            new_val, msg = callback(event)
            if new_val != current_val:
                diff = new_val - current_val
                sign = "+" if diff > 0 else ""
                log_msg.append(f"{msg} ({sign}{diff})")
                current_val = new_val
                event.value = new_val  # Update for next listener

        if log_msg:
            st.toast(f"Event {event.trigger.name}: " + ", ".join(log_msg))
        return current_val


# --- 2. ENTITIES (Сущности) ---

@dataclass
class UnitStats:
    hp: int = 100
    stagger: int = 50
    # Resists: 1.0 = Normal, 0.5 = Endured, 2.0 = Fatal
    resists: Dict[DamageType, float] = field(default_factory=lambda: {
        DamageType.SLASH: 1.0,
        DamageType.PIERCE: 1.0,
        DamageType.BLUNT: 1.0
    })


class Unit:
    def __init__(self, name: str, stats: UnitStats):
        self.name = name
        self.stats = stats
        self.current_hp = stats.hp
        self.current_stagger = stats.stagger
        self.passives = []

    def add_passive(self, passive_func):
        self.passives.append(passive_func)

    def take_damage(self, amount: int, dmg_type: DamageType) -> int:
        multiplier = self.stats.resists.get(dmg_type, 1.0)
        final_dmg = int(amount * multiplier)
        self.current_hp = max(0, self.current_hp - final_dmg)
        return final_dmg


# --- 3. SYSTEM LOGIC (Логика расчета) ---

class BattleSystem:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.bus = EventBus()

    def register_unit_passives(self, unit: Unit):
        # В реальной игре пассивки сами регистрируются при старте боя
        for p in unit.passives:
            # Пример: простая регистрация на Roll
            self.bus.subscribe(TriggerType.ON_ROLL, p)

    def roll_dice(self, min_val: int, max_val: int, source: Unit, target: Unit) -> int:
        base_roll = self.rng.randint(min_val, max_val)

        # Создаем событие для модификации броска
        event = CombatEvent(TriggerType.ON_ROLL, source, target, value=base_roll)
        final_roll = self.bus.emit(event)

        return base_roll, final_roll

    def execute_attack(self, attacker: Unit, target: Unit, min_d: int, max_d: int, d_type: DamageType):
        # 1. Roll Logic
        base, final = self.roll_dice(min_d, max_d, attacker, target)

        # 2. Damage Logic
        damage_dealt = target.take_damage(final, d_type)

        return {
            "base_roll": base,
            "final_roll": final,
            "damage": damage_dealt,
            "type": d_type.value
        }


# --- 4. UI IMPLEMENTATION (Веб-интерфейс "Limroll") ---

st.set_page_config(layout="wide", page_title="Limroll Architect Demo")

# Стилизация под скриншот
st.markdown("""
<style>
    .stButton>button { width: 100%; font-weight: bold; }
    .big-font { font-size: 20px !important; font-weight: bold; }
    .dmg-text { color: #d63031; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("Limroll: Python LoR Architecture Demo")

# --- Sidebar: Configuration ---
with st.sidebar:
    st.header("Global Settings")
    seed_input = st.number_input("RNG Seed", value=42, help="Обеспечивает детерминированность")

    st.header("Debug / Passives")
    st.info("Пример архитектуры пассивок:")
    enable_strength = st.checkbox("Add 'Strength' (+1 Power) to Left Unit")
    enable_fragile = st.checkbox("Add 'Fragile' (+2 Dmg Taken) (Not impl in simple calc)")

# --- Main Layout ---
col_left, col_mid, col_right = st.columns([1, 0.5, 1])

# --- LEFT UNIT SETUP ---
with col_left:
    st.subheader("Attacker (Left)")
    with st.container(border=True):
        l_min = st.number_input("Min Dice", 1, 10, 4, key="l_min")
        l_max = st.number_input("Max Dice", 1, 20, 8, key="l_max")
        l_type = st.selectbox("Type", [t.value for t in DamageType], key="l_type")

        st.markdown("---")
        st.caption("Left Stats (Not used for attack source in this simplified version)")

# --- RIGHT UNIT SETUP ---
with col_right:
    st.subheader("Defender (Right)")
    with st.container(border=True):
        # Resistances mimicking the screenshot
        st.write("Resistances (Multiplier)")
        c1, c2, c3 = st.columns(3)
        r_slash = c1.number_input("Slash", 0.0, 3.0, 1.0, 0.5)
        r_pierce = c2.number_input("Pierce", 0.0, 3.0, 1.0, 0.5)
        r_blunt = c3.number_input("Blunt", 0.0, 3.0, 1.0, 0.5)

        r_hp = st.number_input("Current HP", 0, 100, 50)
        r_stagger = st.number_input("Stagger", 0, 50, 30)

# --- MIDDLE CONTROL ---
with col_mid:
    st.markdown("<br><br>", unsafe_allow_html=True)  # Spacer
    btn_roll = st.button("ROLL ATTACK", type="primary")
    st.markdown("<div style='text-align: center'>VS</div>", unsafe_allow_html=True)

# --- CALCULATION LOGIC ---

if btn_roll:
    # 1. Init System
    sys = BattleSystem(seed=seed_input)

    # 2. Init Units
    attacker = Unit("LeftUnit", UnitStats())

    defender_stats = UnitStats(hp=r_hp, stagger=r_stagger)
    defender_stats.resists = {
        DamageType.SLASH: r_slash,
        DamageType.PIERCE: r_pierce,
        DamageType.BLUNT: r_blunt
    }
    defender = Unit("RightUnit", defender_stats)

    # 3. Add Dynamic Passive (Architectural demo)
    if enable_strength:
        def strength_passive(event: CombatEvent):
            # Проверка: срабатывает только если source это owner пассивки
            if event.source == attacker:
                return event.value + 1, "Strength (+1)"
            return event.value, ""


        sys.bus.subscribe(TriggerType.ON_ROLL, strength_passive)

    # 4. Execute
    d_type_enum = DamageType(l_type)
    result = sys.execute_attack(attacker, defender, l_min, l_max, d_type_enum)

    # 5. Display Results
    st.success("Calculation Complete")

    # Result Columns mimicking "Taken Damage" panels
    res_col1, res_col2 = st.columns(2)

    with res_col1:
        st.info(f"Dice Roll: {result['base_roll']} -> **{result['final_roll']}**")
        if result['base_roll'] != result['final_roll']:
            st.caption("Modified by Passives!")

    with res_col2:
        st.error(f"Damage Dealt: **{result['damage']}**")
        st.caption(f"Resistance: x{defender.stats.resists[d_type_enum]}")
        st.write(f"New HP: {defender.current_hp}")

    # Visualizing the Pipeline
    with st.expander("Show Logic Trace (Architecture Debug)"):
        st.write("1. Seed initialized RNG.")
        st.write(f"2. Base Roll generated: {result['base_roll']}")
        if enable_strength:
            st.write("3. Event `ON_ROLL` trigger caught by `strength_passive`.")
            st.write("4. Value modified +1.")
        st.write(f"5. Final Roll: {result['final_roll']}")
        st.write(f"6. Resistance Calc: {result['final_roll']} * {defender.stats.resists[d_type_enum]}")
        st.write(f"7. HP deducted.")