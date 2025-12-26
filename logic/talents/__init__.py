# logic/talents/__init__.py
from logic.talents.definitions import (
    TalentNakedDefense,
    TalentVengefulPayback,
    TalentBerserkerRage,
    TalentCalmMind
)

TALENT_REGISTRY = {
    "naked_defense": TalentNakedDefense(),
    "vengeful_payback": TalentVengefulPayback(),
    "berserker_rage": TalentBerserkerRage(),
    "calm_mind": TalentCalmMind(),
}