from logic.passives.lilith_passives import PassiveHedonism, PassiveWagTail, PassiveBackstreetDemon, \
    PassiveDaughterOfBackstreets, PassiveBlessingOfWind, PassiveLiveFastDieYoung
from logic.passives.rein_passives import PassiveSCells, PassiveNewDiscovery, TalentRedLycoris, TalentShadowOfMajesty

# === РЕГИСТРАЦИЯ ===
PASSIVE_REGISTRY = {
    "hedonism": PassiveHedonism(),
    "wag_tail": PassiveWagTail(),
    "backstreet_demon": PassiveBackstreetDemon(),
    "daughter_of_backstreets": PassiveDaughterOfBackstreets(),
    "blessing_of_wind": PassiveBlessingOfWind(),
    "live_fast_die_young": PassiveLiveFastDieYoung(),
    "s_cells": PassiveSCells(),
    "new_discovery": PassiveNewDiscovery(),
    "red_lycoris": TalentRedLycoris(),
    "shadow_majesty":TalentShadowOfMajesty()
}