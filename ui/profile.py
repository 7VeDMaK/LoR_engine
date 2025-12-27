import streamlit as st
import random
import os

from core.library import Library
from core.models import Unit
from core.unit_library import UnitLibrary
# ИМПОРТИРУЕМ РЕЕСТРЫ
from logic.passives import PASSIVE_REGISTRY
from logic.talents import TALENT_REGISTRY

ATTR_LABELS = {
    "strength": "Сила", "endurance": "Стойкость", "agility": "Ловкость",
    "wisdom": "Мудрость", "psych": "Психика"
}

# Удаляем Удачу из общего списка, чтобы отрисовать её отдельно
SKILL_LABELS = {
    "strike_power": "Сила удара", "medicine": "Медицина", "willpower": "Сила воли",
    "acrobatics": "Акробатика", "shields": "Щиты",
    "tough_skin": "Крепкая кожа", "speed": "Скорость",
    "light_weapon": "Лёгкое оружие", "medium_weapon": "Среднее оружие",
    "heavy_weapon": "Тяжёлое оружие", "firearms": "Огнестрел",
    "eloquence": "Красноречие", "forging": "Ковка",
    "engineering": "Инженерия", "programming": "Программирование"
}


def save_avatar_file(uploaded, unit_name):
    os.makedirs("data/avatars", exist_ok=True)
    safe = "".join(c for c in unit_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(" ", "_")
    path = f"data/avatars/{safe}.{uploaded.name.split('.')[-1]}"
    with open(path, "wb") as f: f.write(uploaded.getbuffer())
    return path


def render_profile_page():
    if 'roster' not in st.session_state or not st.session_state['roster']:
        st.session_state['roster'] = UnitLibrary.load_all() or {"New Unit": Unit("New Unit")}

    roster = st.session_state['roster']

    # --- ШАПКА ---
    c1, c2 = st.columns([3, 1])
    sel = c1.selectbox("Персонаж", list(roster.keys()))
    if c2.button("➕ Новый"):
        n = f"Unit_{len(roster) + 1}"
        u = Unit(n)
        roster[n] = u
        UnitLibrary.save_unit(u)
        st.rerun()

    unit = roster[sel]

    if st.button("💾 СОХРАНИТЬ ПРОФИЛЬ", type="primary", width='stretch'):
        UnitLibrary.save_unit(unit)
        st.toast("Данные персонажа сохранены!", icon="✅")

    st.divider()

    col_l, col_r = st.columns([1, 2.5], gap="medium")

    # ==========================
    # ЛЕВАЯ КОЛОНКА (Инфо)
    # ==========================
    with col_l:
        # Аватар
        img = unit.avatar if unit.avatar and os.path.exists(
            unit.avatar) else "https://placehold.co/150x150/png?text=No+Image"
        st.image(img, width='stretch')
        upl = st.file_uploader("Загрузить арт", type=['png', 'jpg'], label_visibility="collapsed")
        if upl:
            unit.avatar = save_avatar_file(upl, unit.name)
            UnitLibrary.save_unit(unit)
            st.rerun()

        # Основные данные
        unit.name = st.text_input("Имя", unit.name)

        c_lvl, c_int = st.columns(2)
        unit.level = c_lvl.number_input("Уровень", 1, 100, unit.level)

        # Интеллект
        unit.base_intellect = c_int.number_input("Баз. Инт.", 1, 30, unit.base_intellect)
        total_int = unit.modifiers.get("total_intellect", unit.base_intellect)
        if total_int > unit.base_intellect:
            st.info(f"🧠 Интеллект: **{total_int}** (+{total_int - unit.base_intellect})")
        else:
            st.info(f"🧠 Интеллект: **{total_int}**")

        st.divider()

        # === РАНГ (Два слота) ===
        st.markdown("**Ранг Фиксера**")
        r_c1, r_c2 = st.columns(2)
        unit.rank = r_c1.number_input("Текущий", 1, 12, unit.rank, help="Официальный ранг (12=Zwei, 1=Hana)")

        # Ранг по статусу (храним в памяти или отдельном поле, пока заглушка в memory)
        status_rank = unit.memory.get("status_rank", "9 (Fixer)")
        new_status = r_c2.text_input("Статус", status_rank, help="Ранг, основанный на репутации/сюжете")
        unit.memory["status_rank"] = new_status

        st.divider()

        # Скорость
        st.markdown(f"**🧊 Скорость:**")
        if unit.computed_speed_dice:
            for d in unit.computed_speed_dice:
                st.markdown(f"- {d[0]}~{d[1]}")
        else:
            st.markdown(f"- {unit.base_speed_min}~{unit.base_speed_max}")

    # ==========================
    # ПРАВАЯ КОЛОНКА (Статы)
    # ==========================
    with col_r:
        # 1. Ресурсы и Броня
        with st.expander("⚙️ Состояние и Экипировка", expanded=False):
            c1, c2 = st.columns(2)
            c1.markdown("**Модификаторы (%)**")
            pc1, pc2 = c1.columns(2)
            unit.implants_hp_pct = pc1.number_input("HP Импл %", 0, 500, unit.implants_hp_pct)
            unit.implants_sp_pct = pc2.number_input("SP Импл %", 0, 500, unit.implants_sp_pct)
            unit.talents_hp_pct = pc1.number_input("HP Талант %", 0, 500, unit.talents_hp_pct)
            unit.talents_sp_pct = pc2.number_input("SP Талант %", 0, 500, unit.talents_sp_pct)

            c2.markdown("**Броня и Резисты**")
            unit.armor_name = c2.text_input("Броня", unit.armor_name, placeholder="Название")
            r1, r2, r3 = c2.columns(3)
            unit.hp_resists.slash = r1.number_input("Slash", 0.0, 3.0, unit.hp_resists.slash, step=0.1)
            unit.hp_resists.pierce = r2.number_input("Pierce", 0.0, 3.0, unit.hp_resists.pierce, step=0.1)
            unit.hp_resists.blunt = r3.number_input("Blunt", 0.0, 3.0, unit.hp_resists.blunt, step=0.1)

        # 2. Полоски HP/SP
        with st.container(border=True):
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("HP (Здоровье)", f"{unit.current_hp} / {unit.max_hp}")
            sc2.metric("SP (Рассудок)", f"{unit.current_sp} / {unit.max_sp}")
            sc3.metric("Stagger (Выдержка)", f"{unit.current_stagger} / {unit.max_stagger}")

            # Инпуты для ручной правки
            c_edit1, c_edit2, c_edit3 = st.columns(3)
            unit.current_hp = c_edit1.number_input("Set HP", 0, 9999, unit.current_hp, label_visibility="collapsed")
            unit.current_sp = c_edit2.number_input("Set SP", -999, 999, unit.current_sp, label_visibility="collapsed")
            unit.current_stagger = c_edit3.number_input("Set Stg", 0, 9999, unit.current_stagger,
                                                        label_visibility="collapsed")

        # 3. Характеристики (5 колонок)
        st.subheader("Характеристики")
        acols = st.columns(5)
        attr_keys = ["strength", "endurance", "agility", "wisdom", "psych"]

        for i, k in enumerate(attr_keys):
            base_val = unit.attributes[k]
            total_val = unit.modifiers.get(f"total_{k}", base_val)

            with acols[i]:
                st.caption(ATTR_LABELS[k])
                c_in, c_val = st.columns([1.5, 1])
                with c_in:
                    new_base = st.number_input("Base", 0, 999, base_val, key=f"attr_{k}", label_visibility="collapsed")
                    unit.attributes[k] = new_base
                with c_val:
                    st.write("")  # Spacer
                    if total_val > new_base:
                        st.markdown(f":green[**{total_val}**]")
                    elif total_val < new_base:
                        st.markdown(f":red[**{total_val}**]")
                    else:
                        st.markdown(f"**{total_val}**")

        # 4. УДАЧА (Два слота)
        st.divider()
        st.subheader("🍀 Удача")
        l_col1, l_col2, _ = st.columns([1, 1, 2])

        # Слот 1: Стат (Навык)
        with l_col1:
            st.caption("Стат (Навык)")
            base_luck = unit.skills.get("luck", 0)
            total_luck = unit.modifiers.get("total_luck", base_luck)

            lc_in, lc_val = st.columns([1.5, 1])
            with lc_in:
                new_luck_skill = st.number_input("Luck Skill", 0, 999, base_luck, label_visibility="collapsed")
                unit.skills["luck"] = new_luck_skill
            with lc_val:
                st.write("")
                if total_luck > new_luck_skill:
                    st.markdown(f":green[**{total_luck}**]")
                else:
                    st.markdown(f"**{total_luck}**")

        # Слот 2: Текущая удача (Ресурс)
        with l_col2:
            st.caption("Текущая (Points)")
            # Храним в resources, т.к. это изменяемый в бою параметр
            cur_luck = unit.resources.get("luck", 0)
            new_cur_luck = st.number_input("Current Luck", 0, 999, cur_luck, label_visibility="collapsed",
                                           help="Расходуемый ресурс удачи")
            unit.resources["luck"] = new_cur_luck

        # 5. Остальные Навыки
        st.markdown("")
        with st.expander("📚 Остальные навыки", expanded=True):
            scols = st.columns(3)
            skill_list = list(SKILL_LABELS.keys())

            for i, k in enumerate(skill_list):
                col_idx = i % 3
                with scols[col_idx]:
                    base_val = unit.skills.get(k, 0)
                    total_val = unit.modifiers.get(f"total_{k}", base_val)

                    st.caption(SKILL_LABELS[k])
                    c_in, c_val = st.columns([1.5, 1])
                    with c_in:
                        new_base = st.number_input("S", 0, 999, base_val, key=f"sk_{k}", label_visibility="collapsed")
                        unit.skills[k] = new_base
                    with c_val:
                        st.write("")
                        if total_val > new_base:
                            st.markdown(f":green[**{total_val}**]")
                        elif total_val < new_base:
                            st.markdown(f":red[**{total_val}**]")
                        else:
                            st.markdown(f"**{total_val}**")

    # ПЕРЕСЧЕТ СТАТОВ
    logs = unit.recalculate_stats()

    st.markdown("---")

    # === КОЛОДА ===
    st.subheader("🃏 Боевая колода")
    all_library_cards = Library.get_all_cards()
    card_map = {c.id: c for c in all_library_cards}
    all_card_ids = [c.id for c in all_library_cards]

    valid_deck = [cid for cid in unit.deck if cid in card_map]

    sel_deck = st.multiselect(
        "Состав колоды:",
        options=all_card_ids,
        default=valid_deck,
        format_func=lambda x: f"{card_map[x].name} [{card_map[x].tier}]" if x in card_map else x
    )
    if sel_deck != unit.deck:
        unit.deck = sel_deck

    st.caption(f"Всего карт: {len(unit.deck)}")

    st.markdown("---")

    # === СПОСОБНОСТИ ===
    st.subheader("🧬 Таланты и Пассивки")

    c_tal, c_desc = st.columns([2, 1])

    def fmt_name(aid):
        if aid in TALENT_REGISTRY: return f"★ {TALENT_REGISTRY[aid].name}"
        if aid in PASSIVE_REGISTRY: return f"🛡️ {PASSIVE_REGISTRY[aid].name}"
        return aid

    with c_tal:
        # Таланты
        max_talents = unit.level // 3
        st.markdown(f"**Таланты ({len(unit.talents)} / {max_talents})**")
        unit.talents = st.multiselect(
            "Список талантов",
            options=sorted(list(TALENT_REGISTRY.keys())),
            default=[t for t in unit.talents if t in TALENT_REGISTRY],
            format_func=fmt_name,
            max_selections=max_talents,
            label_visibility="collapsed",
            key=f"mt_{unit.name}"
        )

        # Пассивки
        st.markdown("**Пассивки**")
        unit.passives = st.multiselect(
            "Список пассивок",
            options=sorted(list(PASSIVE_REGISTRY.keys())),
            default=[p for p in unit.passives if p in PASSIVE_REGISTRY],
            format_func=fmt_name,
            label_visibility="collapsed",
            key=f"mp_{unit.name}"
        )

    with c_desc:
        st.info("ℹ️ **Эффекты:**")
        all_ids = unit.talents + unit.passives
        if not all_ids:
            st.caption("Пусто")
        for aid in all_ids:
            obj = TALENT_REGISTRY.get(aid) or PASSIVE_REGISTRY.get(aid)
            if obj:
                with st.expander(obj.name):
                    st.write(obj.description)

    # === ЛОГ РАСЧЕТОВ ===
    with st.expander("📜 Лог расчета характеристик"):
        for l in logs:
            st.caption(f"• {l}")