import streamlit as st
from core.models import Unit, Dice, DiceType, Card, Resistances
from core.library import Library
from ui.styles import TYPE_ICONS, TYPE_COLORS


# --- ПЕРЕВОДЧИК СКРИПТОВ ---
def _format_script_text(script_id: str, params: dict) -> str:
    """Форматирует технические ID скриптов в читаемый текст."""
    if script_id == "restore_hp":
        amt = params.get("amount", 0)
        return f"💚 Восстановить {amt} HP"
    elif script_id == "apply_status":
        status = params.get("status", "???").capitalize()
        stack = params.get("stack", 0)
        target = params.get("target", "target")
        tgt_str = " (на себя)" if target == "self" else ""
        return f"🧪 Наложить {stack} {status}{tgt_str}"
    return f"🔧 {script_id} {params}"


def render_unit_stats(unit: Unit):
    """Отображает основные показатели юнита (HP, Stagger, SP) и активные статусы."""
    icon = '🟦' if 'Roland' in unit.name else '🟥'
    st.markdown(f"### {icon} {unit.name} (Lvl {unit.level})")

    # HP (Здоровье)
    max_hp = unit.max_hp if unit.max_hp > 0 else 1
    hp_pct = max(0.0, min(1.0, unit.current_hp / max_hp))
    st.progress(hp_pct, text=f"HP: {unit.current_hp}/{unit.max_hp}")

    # Stagger (Ошеломление)
    max_stg = unit.max_stagger if unit.max_stagger > 0 else 1
    stg_pct = max(0.0, min(1.0, unit.current_stagger / max_stg))
    st.progress(stg_pct, text=f"Stagger: {unit.current_stagger}/{unit.max_stagger}")

    # Sanity (SP / Рассудок)
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

    # === ОТОБРАЖЕНИЕ СТАТУС-ЭФФЕКТОВ ===
    # Получаем суммарные стаки через UnitStatusMixin
    active_statuses = unit.statuses
    if active_statuses:
        st.markdown("---")
        # Словарь иконок для различных эффектов
        status_icons = {
            "self_control": "💨",
            "strength": "💪",
            "bleed": "🩸",
            "paralysis": "⚡",
            "haste": "👟",
            "protection": "🛡️",
            "barrier": "🟡"
        }

        # Динамическое создание колонок под количество статусов
        cols = st.columns(max(4, len(active_statuses)))
        for i, (name, val) in enumerate(active_statuses.items()):
            with cols[i % 4]:
                icon = status_icons.get(name, "✨")
                label = name.replace('_', ' ').capitalize()
                st.metric(label=f"{icon} {label}", value=val)


def render_combat_info(unit: Unit):
    """Отображает сопротивления и боевые бонусы юнита."""
    with st.expander("🛡️ Resists & Bonuses", expanded=False):
        # Резисты
        c1, c2, c3 = st.columns(3)
        c1.metric("Slash", f"x{unit.hp_resists.slash}")
        c2.metric("Pierce", f"x{unit.hp_resists.pierce}")
        c3.metric("Blunt", f"x{unit.hp_resists.blunt}")

        st.divider()

        # Бонусы от характеристик и навыков
        mods = unit.modifiers
        atk_power = mods.get("power_attack", 0) + mods.get("power_medium", 0)
        def_block = mods.get("power_block", 0)
        def_evade = mods.get("power_evade", 0)
        init_bonus = mods.get("initiative", 0)

        b1, b2, b3 = st.columns(3)
        b1.metric("⚔️ Atk Power", f"+{atk_power}")
        b2.metric("🛡️ Block", f"+{def_block}")
        b3.metric("💨 Evade", f"+{def_evade}")

        st.caption(f"Init Bonus: +{init_bonus}")


def card_selector_ui(unit: Unit, key_prefix: str):
    """Интерфейс выбора карты из библиотеки или создания кастомной."""
    mode = st.radio("Src", ["📚 Library", "🛠️ Custom"], key=f"{key_prefix}_mode", horizontal=True,
                    label_visibility="collapsed")

    if mode == "📚 Library":
        all_cards_objs = Library.get_all_cards()
        if not all_cards_objs:
            st.error("Library empty!")
            return None

        selected_card = st.selectbox(
            "Preset",
            all_cards_objs,
            format_func=lambda x: x.name,
            key=f"{key_prefix}_lib"
        )
        if selected_card and selected_card.description:
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
    """Визуальное представление карты с её кубиками и эффектами."""
    with st.container(border=True):
        if is_staggered:
            st.error("😵 STAGGERED")
            return
        if not card:
            st.warning("No card selected")
            return

        type_icon = "🏹" if card.card_type == "ranged" else "⚔️"
        st.markdown(f"**{card.name}** {type_icon}")

        # Скрипты карты (On Use и т.д.)
        if card.scripts:
            for trig, scripts in card.scripts.items():
                trigger_name = trig.replace("_", " ").title()
                st.markdown(f"**{trigger_name}:**")
                for s in scripts:
                    friendly_text = _format_script_text(s['script_id'], s.get('params', {}))
                    st.caption(f"- {friendly_text}")

        st.divider()

        # Кубики карты
        cols = st.columns(len(card.dice_list)) if card.dice_list else [st]
        for i, dice in enumerate(card.dice_list):
            with cols[i]:
                color = TYPE_COLORS.get(dice.dtype, "black")
                icon = TYPE_ICONS.get(dice.dtype, "?")
                st.markdown(f":{color}[{icon} **{dice.min_val}-{dice.max_val}**]")

                if dice.scripts:
                    for trig, effs in dice.scripts.items():
                        for e in effs:
                            friendly_text = _format_script_text(e['script_id'], e.get('params', {}))
                            st.caption(f"*{friendly_text}*")