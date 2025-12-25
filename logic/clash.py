# logic/clash.py
from core.models import Dice, DiceType, Unit, Resistances
import random


class ClashSystem:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()

    def roll(self, dice: Dice) -> int:
        val = self.rng.randint(dice.min_val, dice.max_val)
        dice.current_val = val
        return val

    def is_attack(self, dice: Dice) -> bool:
        return dice.dtype in [DiceType.SLASH, DiceType.PIERCE, DiceType.BLUNT]

    def get_multiplier(self, dtype: DiceType, resists: Resistances) -> float:
        if dtype == DiceType.SLASH: return resists.slash
        if dtype == DiceType.PIERCE: return resists.pierce
        if dtype == DiceType.BLUNT: return resists.blunt
        return 1.0

    def apply_damage(self, target: Unit, amount: int, dtype: DiceType, is_stagger_dmg: bool = False):
        """Применяет резисты и вычитает HP/Stagger"""
        if amount <= 0: return 0

        if is_stagger_dmg:
            mult = self.get_multiplier(dtype, target.stagger_resists)
            final = int(amount * mult)
            target.current_stagger -= final
            return final
        else:
            # Обычный урон бьет и по HP, и по Stagger (обычно)
            # В LoR урон по HP идет с HP резистом, а по Stagger с Stagger резистом
            hp_mult = self.get_multiplier(dtype, target.hp_resists)
            stagger_mult = self.get_multiplier(dtype, target.stagger_resists)

            final_hp = int(amount * hp_mult)
            final_stagger = int(amount * stagger_mult)

            target.current_hp -= final_hp
            target.current_stagger -= final_stagger
            return final_hp

    def resolve_card_clash(self, attacker: Unit, defender: Unit):
        queue_a = [d for d in attacker.current_card.dice_list]
        queue_b = [d for d in defender.current_card.dice_list]

        log = []
        round_num = 1

        while queue_a and queue_b:
            # Если кто-то в стаггере - он не может кидать кубики (теряет их)
            # (Упрощенно: просто прерываем бой или даем free hit, но пока оставим как есть)

            die_a = queue_a.pop(0)
            die_b = queue_b.pop(0)

            val_a = self.roll(die_a)
            val_b = self.roll(die_b)

            entry = {
                "round": round_num,
                "rolls": f"🔵 {die_a.dtype.value}({val_a}) vs 🔴 {die_b.dtype.value}({val_b})",
                "details": ""
            }

            # === 1. АТАКА vs АТАКА ===
            if self.is_attack(die_a) and self.is_attack(die_b):
                if val_a > val_b:
                    dmg = self.apply_damage(defender, val_a, die_a.dtype)
                    entry["details"] = f"A Wins! Deals {dmg} HP Dmg"
                elif val_b > val_a:
                    dmg = self.apply_damage(attacker, val_b, die_b.dtype)
                    entry["details"] = f"B Wins! Deals {dmg} HP Dmg"
                else:
                    entry["details"] = "Clash Draw"

            # === 2. АТАКА (A) vs ЗАЩИТА (B) ===
            elif self.is_attack(die_a) and not self.is_attack(die_b):
                entry["details"] = self._resolve_atk_vs_def(attacker, val_a, die_a,
                                                            defender, val_b, die_b, queue_b)

            # === 3. ЗАЩИТА (A) vs АТАКА (B) ===
            elif not self.is_attack(die_a) and self.is_attack(die_b):
                entry["details"] = self._resolve_atk_vs_def(defender, val_b, die_b,
                                                            attacker, val_a, die_a, queue_a)

            # === 4. ЗАЩИТА vs ЗАЩИТА ===
            else:
                diff = abs(val_a - val_b)
                if val_a > val_b:
                    # Победитель наносит Stagger урон
                    dmg = self.apply_damage(defender, diff, DiceType.BLUNT, is_stagger_dmg=True)
                    entry["details"] = f"Def vs Def: A Wins. Deals {dmg} Stagger Dmg"
                    # Логика эвейда: если A был Evade, он возвращается
                    if die_a.dtype == DiceType.EVADE:
                        queue_a.insert(0, die_a)
                        entry["details"] += " (Evade Recycled)"

                elif val_b > val_a:
                    dmg = self.apply_damage(attacker, diff, DiceType.BLUNT, is_stagger_dmg=True)
                    entry["details"] = f"Def vs Def: B Wins. Deals {dmg} Stagger Dmg"
                    if die_b.dtype == DiceType.EVADE:
                        queue_b.insert(0, die_b)
                        entry["details"] += " (Evade Recycled)"
                else:
                    entry["details"] = "Def Draw. Nothing happens."

            log.append(entry)
            round_num += 1

        # One-Sided
        log.extend(self._resolve_onesided(queue_a, attacker, defender))
        log.extend(self._resolve_onesided(queue_b, defender, attacker))

        return log

    def _resolve_atk_vs_def(self, atk_unit, atk_val, atk_die, def_unit, def_val, def_die, def_queue):
        """Атака (atk) бьет в Защиту (def). Возвращает строку лога."""

        # VS BLOCK
        if def_die.dtype == DiceType.BLOCK:
            if atk_val > def_val:
                dmg_val = atk_val - def_val
                real_dmg = self.apply_damage(def_unit, dmg_val, atk_die.dtype)
                return f"Block Broken! {real_dmg} HP Dmg dealt"
            else:
                stagger_val = def_val - atk_val
                real_stagger = self.apply_damage(atk_unit, stagger_val, DiceType.BLUNT, is_stagger_dmg=True)
                return f"Blocked! Attacker takes {real_stagger} Stagger Dmg"

        # VS EVADE
        elif def_die.dtype == DiceType.EVADE:
            if atk_val > def_val:
                real_dmg = self.apply_damage(def_unit, atk_val, atk_die.dtype)
                return f"Evade Failed! {real_dmg} HP Dmg dealt"
            else:
                # Эвейд успешен -> Ресайкл.
                # Опционально: можно восстановить стаггер (def_unit.current_stagger += val)
                def_queue.insert(0, def_die)
                return "Evade Success! Recycled."

        return "Unknown Def Type"

    def _resolve_onesided(self, queue, attacker, defender):
        log = []
        while queue:
            die = queue.pop(0)
            val = self.roll(die)

            if self.is_attack(die):
                dmg = self.apply_damage(defender, val, die.dtype)
                txt = f"One-Sided Hit! {dmg} HP Dmg"
            else:
                txt = "Defensive die wasted in one-sided"

            log.append({
                "round": "One-Sided",
                "rolls": f"{die.dtype.value}({val})",
                "details": txt
            })
        return log