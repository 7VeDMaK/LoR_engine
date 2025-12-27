# logic/talents/__init__.py
from logic.talents.branch_1_mindgames import TalentKeepItTogether, TalentCenterOfBalance
from logic.talents.branch_5_berseker import *
from logic.talents.branch_6_smoker import *
from logic.talents.branch_9_shadow import TalentRevenge

TALENT_REGISTRY = {
    "naked_defense": TalentNakedDefense(),
    "vengeful_payback": TalentVengefulPayback(),
    "berserker_rage": TalentBerserkerRage(),
    "calm_mind": TalentCalmMind(),
    "hiding_in_smoke": TalentHidingInSmoke(),
    "smoke_universality": TalentSmokeUniversality(),
    "frenzy": TalentFrenzy(),
    "keep_it_together": TalentKeepItTogether(), # <--- Регистрация
    "center_of_balance": TalentCenterOfBalance(),
    "revenge": TalentRevenge(),
}
