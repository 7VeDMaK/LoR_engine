# logic/talents/__init__.py
from logic.talents.branch_5_berseker import *
from logic.talents.branch_6_smoker import *

TALENT_REGISTRY = {
    "naked_defense": TalentNakedDefense(),
    "vengeful_payback": TalentVengefulPayback(),
    "berserker_rage": TalentBerserkerRage(),
    "calm_mind": TalentCalmMind(),
    "hiding_in_smoke": TalentHidingInSmoke(),
    "smoke_universality": TalentSmokeUniversality(),
    "frenzy": TalentFrenzy(),
}
