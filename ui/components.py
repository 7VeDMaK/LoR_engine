import streamlit as st
from core.models import Unit, Dice, DiceType, Card, Resistances
from core.library import Library
from ui.styles import TYPE_ICONS, TYPE_COLORS


def render_unit_stats(unit: Unit):
    icon = '🟦' if 'Roland' in unit.name else '🟥'
    st.markdown(f"### {icon} {unit.name}")

    # HP
    max_hp = unit.max_hp if unit.max_hp > 0 else 1
    hp_pct = max(0.0, min(1.0, unit.current_hp / max_hp))
    st.progress(hp_pct, text=f"HP: {unit.current_hp}/{unit.max_hp}")

    # Stagger
    max_stg = unit.max_stagger if unit.max_stagger > 0 else 1
    stg_pct = max(0.0, min(1.0, unit.current_stagger / max_stg))
    st.progress(stg_pct, text=f"Stagger: {unit.current_stagger}/{unit.max_stagger}")

    # Sanity (SP)
    sp_limit = unit.max_sp
    total_range = sp_limit * 2 if sp_limit > 0 else 1
    current_shifted = unit.current_sp + sp_limit
    sp_pct = max(0.0, min(1.0, current_shifted / total_range))

    mood = "😐"
    if unit.current_sp >= 20:
        mood = "🙂"
    elif unit.current_sp >= 40:
        mood = "😄"
    elif unit.current_sp <= -20:
        mood = "😨"
    elif unit.current_sp <= -40:
        mood = "😱"

    st.progress(sp_pct, text=f"Sanity: {unit.current_sp}/{unit.max_sp} {mood}")

    # Statuses
    if unit.statuses:
        st.markdown("---")
        cols = st.columns(4)
        idx = 0
        for name, val in unit.statuses.items():
            with cols[idx % 4]:
                st.metric(label=name.capitalize(), value=val)
            idx += 1


def render_resist_inputs(unit: Unit, key_prefix: str):
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


def card_selector_ui(unit: Unit, key_prefix: str):
    mode = st.radio("Src", ["📚 Library", "🛠️ Custom"], key=f"{key_prefix}_mode", horizontal=True,
                    label_visibility="collapsed")

    if mode == "📚 Library":
        all_cards_objs = Library.get_all_cards()
        if not all_cards_objs:
            st.error("Library empty!")
            return None

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

            selected_card = Card(name=c_name, dice_list=custom_dice, description="Custom Card")

    if not unit.is_staggered():
        unit.current_card = selected_card
    return unit.current_card


def render_card_visual(card: Card, is_staggered: bool = False):
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