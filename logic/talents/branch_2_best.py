from logic.passives.base_passive import BasePassive

# ==========================================
# 2.3 Тактический анализ (Заглушка)
# ==========================================
class TalentTacticalAnalysis(BasePassive):
    id = "tactical_analysis"
    name = "Тактический анализ"
    description = "Заглушка. Позволяет видеть детальную информацию о намерениях противника."
    is_active_ability = False