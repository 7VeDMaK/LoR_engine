# logic/talents/__init__.py
from logic.talents.definitions import (
    TalentNakedDefense,
    TalentVengefulPayback,
    TalentBerserkerRage,
    TalentCalmMind,
    TalentHidingInSmoke,
    TalentSmokeUniversality,
    TalentFrenzy
)

TALENT_REGISTRY = {
    "naked_defense": TalentNakedDefense(),
    "vengeful_payback": TalentVengefulPayback(),
    "berserker_rage": TalentBerserkerRage(),
    "calm_mind": TalentCalmMind(),
    "hiding_in_smoke": TalentHidingInSmoke(),
    "smoke_universality": TalentSmokeUniversality(),
    "frenzy": TalentFrenzy(),
}