from logic.passives.base_passive import BasePassive


class PassiveSCells(BasePassive):
    id = "s_cells"
    name = "S-клетки"
    description = "В начале боя восстанавливает 10 HP за каждый имеющийся слот скорости."

    def on_combat_start(self, unit, log_func):
        # Считаем количество активных слотов (кубиков скорости)
        dice_count = len(unit.active_slots)

        if dice_count > 0:
            heal_amount = dice_count * 10
            actual_heal = unit.heal_hp(heal_amount)

            if log_func:
                log_func(f"🧬 {self.name}: {dice_count} слотов x 10 = Восстановлено {actual_heal} HP")