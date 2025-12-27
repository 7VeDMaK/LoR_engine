import sys
import streamlit as st
from contextlib import contextmanager
from io import StringIO

from core.models import Unit
from core.library import Library  # <--- ОБЯЗАТЕЛЬНО
from logic.clash import ClashSystem
from logic.passives.__init__ import PASSIVE_REGISTRY
from logic.statuses import StatusManager
from logic.talents import TALENT_REGISTRY


@contextmanager
def capture_output():
    new_out = StringIO()
    old_out = sys.stdout
    try:
        sys.stdout = new_out
        yield new_out
    finally:
        sys.stdout = old_out


def roll_phase():
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']
    p1.recalculate_stats();
    p2.recalculate_stats()

    def process_roll(unit):
        if unit.is_staggered():
            unit.active_slots = [
                {'speed': 0, 'card': None, 'target_slot': -1, 'is_aggro': False, 'force_clash': False, 'stunned': True}]
        else:
            unit.roll_speed_dice()
            for s in unit.active_slots: s['force_clash'] = False

    process_roll(p1);
    process_roll(p2)
    max_len = max(len(p1.active_slots), len(p2.active_slots))
    for i in range(max_len):
        if i < len(p1.active_slots) and not p1.active_slots[i].get('stunned'):
            p1.active_slots[i]['target_slot'] = i if i < len(p2.active_slots) else -1
        if i < len(p2.active_slots) and not p2.active_slots[i].get('stunned'):
            p2.active_slots[i]['target_slot'] = i if i < len(p1.active_slots) else -1
    st.session_state['phase'] = 'planning'
    st.session_state['turn_message'] = "🎲 Speed Rolled!"


def step_start():
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']
    sys_clash = ClashSystem()
    init_logs, actions = sys_clash.prepare_turn(p1, p2)
    st.session_state['battle_logs'] = init_logs
    st.session_state['turn_actions'] = actions
    st.session_state['executed_p1'] = set()
    st.session_state['executed_p2'] = set()
    st.session_state['turn_phase'] = 'fighting'
    st.session_state['action_idx'] = 0


def step_next():
    actions = st.session_state['turn_actions']
    idx = st.session_state['action_idx']
    if idx < len(actions):
        sys_clash = ClashSystem()
        act = actions[idx]
        logs = sys_clash.execute_single_action(act, st.session_state['executed_p1'], st.session_state['executed_p2'])
        st.session_state['battle_logs'].extend(logs)
        st.session_state['action_idx'] += 1
    if st.session_state['action_idx'] >= len(actions): step_finish()


def step_finish():
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']
    sys_clash = ClashSystem()
    end_logs = sys_clash.finalize_turn(p1, p2)
    st.session_state['battle_logs'].extend(end_logs)
    finish_round_logic()


def execute_combat_auto():
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']
    sys_clash = ClashSystem()
    with capture_output() as captured:
        logs = sys_clash.resolve_turn(p1, p2)
    st.session_state['battle_logs'] = logs
    st.session_state['script_logs'] = captured.getvalue()
    finish_round_logic()


def finish_round_logic():
    p1 = st.session_state['attacker']
    p2 = st.session_state['defender']
    msg = []
    if p1.active_slots and p1.active_slots[0].get('stunned'): p1.current_stagger = p1.max_stagger; msg.append(
        f"✨ {p1.name} recovered!")
    if p2.active_slots and p2.active_slots[0].get('stunned'): p2.current_stagger = p2.max_stagger; msg.append(
        f"✨ {p2.name} recovered!")
    st.session_state['turn_message'] = " ".join(msg) if msg else "Round Complete."

    def trigger_end(unit, prefix):
        logs = []
        for pid in unit.passives:
            if pid in PASSIVE_REGISTRY: PASSIVE_REGISTRY[pid].on_round_end(unit, lambda m: logs.append(m))
        for pid in unit.talents:
            if pid in TALENT_REGISTRY: TALENT_REGISTRY[pid].on_round_end(unit, lambda m: logs.append(m))
        logs.extend(StatusManager.process_turn_end(unit))
        unit.tick_cooldowns()
        if logs: st.session_state['battle_logs'].append({"round": "End", "details": ", ".join(logs)})

    trigger_end(p1, "P1");
    trigger_end(p2, "P2")
    p1.active_slots = [];
    p2.active_slots = []
    st.session_state['phase'] = 'roll'
    st.session_state['turn_phase'] = 'done'


def execute_combat():  # Legacy wrapper
    execute_combat_auto()


def reset_game():
    for key in ['attacker', 'defender']:
        if key in st.session_state:
            u = st.session_state[key]
            u.recalculate_stats()
            u.current_hp = u.max_hp;
            u.current_stagger = u.max_stagger;
            u.current_sp = u.max_sp
            u._status_effects = {};
            u.delayed_queue = [];
            u.active_slots = [];
            u.cooldowns = {};
            u.active_buffs = {};
            u.memory = {}
    st.session_state['battle_logs'] = [];
    st.session_state['script_logs'] = "";
    st.session_state['turn_message'] = "";
    st.session_state['phase'] = 'roll'


def sync_state_from_widgets(unit: Unit, key_prefix: str):
    for i, slot in enumerate(unit.active_slots):
        if slot.get('stunned'): continue

        # 1. CARD (Имя -> Объект)
        lib_key = f"{key_prefix}_lib_{i}"
        if lib_key in st.session_state:
            card_name = st.session_state[lib_key]
            slot['card'] = Library.get_card(card_name)

        # 2. TARGET
        tgt_key = f"{key_prefix}_tgt_{i}"
        if tgt_key in st.session_state:
            slot['target_slot'] = st.session_state[tgt_key]

        # 3. AGGRO
        aggro_key = f"{key_prefix}_aggro_{i}"
        if aggro_key in st.session_state:
            slot['is_aggro'] = st.session_state[aggro_key]

        # 4. PREVENT REDIRECTION
        ign_key = f"{key_prefix}_ign_{i}"
        if ign_key in st.session_state:
            slot['prevent_redirection'] = st.session_state[ign_key]


def precalculate_interactions(p1: Unit, p2: Unit):
    ClashSystem.calculate_redirections(p1, p2)
    ClashSystem.calculate_redirections(p2, p1)

    def _calc_ui(me, enemy):
        for i, my_slot in enumerate(me.active_slots):
            if my_slot.get('stunned'):
                my_slot['ui_status'] = {"text": "😵 STAGGERED", "icon": "❌", "color": "gray"}
                continue

            target_idx = my_slot.get('target_slot', -1)
            status = {"text": "⛔ NO TARGET", "icon": "⛔", "color": "gray"}

            if target_idx != -1 and target_idx < len(enemy.active_slots):
                enemy_slot = enemy.active_slots[target_idx]
                if enemy_slot.get('target_slot') == i:
                    status = {"text": f"CLASH S{target_idx + 1}", "icon": "⚔️", "color": "red"}
                else:
                    status = {"text": f"ATK S{target_idx + 1}", "icon": "🏹", "color": "orange"}

            my_slot['ui_status'] = status

    _calc_ui(p1, p2)
    _calc_ui(p2, p1)