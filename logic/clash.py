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
        mapping = {
            DiceType.SLASH: resists.slash,
            DiceType.PIERCE: resists.pierce,
            DiceType.BLUNT: resists.blunt
        }
        return mapping.get(dtype, 1.0)

    def apply_damage(self, target: Unit, amount: int, dtype: DiceType, is_stagger_dmg: bool = False):
        if amount <= 0: return 0

        if is_stagger_dmg:
            mult = self.get_multiplier(dtype, target.stagger_resists)
            final = int(amount * mult)
            target.current_stagger = max(0, target.current_stagger - final)
            return final
        else:
            hp_mult = self.get_multiplier(dtype, target.hp_resists)
            stg_mult = self.get_multiplier(dtype, target.stagger_resists)

            final_hp = int(amount * hp_mult)
            final_stg = int(amount * stg_mult)

            target.current_hp = max(0, target.current_hp - final_hp)
            target.current_stagger = max(0, target.current_stagger - final_stg)
            return final_hp

    def restore_stagger(self, unit: Unit, amount: int):
        """Восстанавливает стаггер (не выше максимума)"""
        unit.current_stagger = min(unit.max_stagger, unit.current_stagger + amount)
        return amount

    def resolve_card_clash(self, attacker: Unit, defender: Unit):
        # Копируем дайсы, чтобы не удалять их из оригинальной карты
        queue_a = [d for d in attacker.current_card.dice_list]
        queue_b = [d for d in defender.current_card.dice_list]

        log = []
        round_num = 1

        while queue_a and queue_b:
            if attacker.is_staggered() or defender.is_staggered():
                log.append({"round": round_num, "rolls": "---", "details": "Opponent Staggered! Clash ends."})
                break

            die_a = queue_a.pop(0)
            die_b = queue_b.pop(0)
            val_a = self.roll(die_a)
            val_b = self.roll(die_b)

            entry = {
                "round": round_num,
                "rolls": f"🔵 {die_a.dtype.value}({val_a}) vs 🔴 {die_b.dtype.value}({val_b})",
                "details": ""
            }

            # 1. ATK vs ATK
            if self.is_attack(die_a) and self.is_attack(die_b):
                if val_a > val_b:
                    dmg = self.apply_damage(defender, val_a, die_a.dtype)
                    entry["details"] = f"A Wins! Deals {dmg} HP"
                elif val_b > val_a:
                    dmg = self.apply_damage(attacker, val_b, die_b.dtype)
                    entry["details"] = f"B Wins! Deals {dmg} HP"
                else:
                    entry["details"] = "Clash Draw"

            # 2. ATK vs DEF
            elif self.is_attack(die_a) and not self.is_attack(die_b):
                entry["details"] = self._resolve_atk_vs_def(attacker, val_a, die_a,
                                                            defender, val_b, die_b, queue_b)

            # 3. DEF vs ATK
            elif not self.is_attack(die_a) and self.is_attack(die_b):
                entry["details"] = self._resolve_atk_vs_def(defender, val_b, die_b,
                                                            attacker, val_a, die_a, queue_a)

            # 4. DEF vs DEF
            else:
                diff = abs(val_a - val_b)
                if val_a > val_b:
                    dmg = self.apply_damage(defender, diff, DiceType.BLUNT, is_stagger_dmg=True)
                    entry["details"] = f"Def Wins! Deals {dmg} Stagger"
                    # Если выиграл Evade - он восстанавливает стаггер, но НЕ ресайклится об защиту
                    if die_a.dtype == DiceType.EVADE:
                        rec = self.restore_stagger(attacker, val_a)
                        entry["details"] += f" (Recover {rec} Stg)"

                elif val_b > val_a:
                    dmg = self.apply_damage(attacker, diff, DiceType.BLUNT, is_stagger_dmg=True)
                    entry["details"] = f"Def Wins! Deals {dmg} Stagger"
                    if die_b.dtype == DiceType.EVADE:
                        rec = self.restore_stagger(defender, val_b)
                        entry["details"] += f" (Recover {rec} Stg)"
                else:
                    entry["details"] = "Draw. Both wasted."

            log.append(entry)
            round_num += 1

        # One-Sided
        log.extend(self._resolve_onesided(queue_a, attacker, defender))
        log.extend(self._resolve_onesided(queue_b, defender, attacker))

        return log

    def _resolve_atk_vs_def(self, atk_unit, atk_val, atk_die, def_unit, def_val, def_die, def_queue):
        # VS BLOCK
        if def_die.dtype == DiceType.BLOCK:
            if atk_val > def_val:
                dmg = self.apply_damage(def_unit, atk_val - def_val, atk_die.dtype)
                return f"Block Broken! {dmg} HP Dmg"
            else:
                stg = self.apply_damage(atk_unit, def_val - atk_val, DiceType.BLUNT, is_stagger_dmg=True)
                return f"Blocked! Reflected {stg} Stagger Dmg"

        # VS EVADE
        elif def_die.dtype == DiceType.EVADE:
            if atk_val > def_val:
                dmg = self.apply_damage(def_unit, atk_val, atk_die.dtype)
                return f"Evade Failed! {dmg} HP Dmg"
            else:
                # Evade Success: Recycle + Restore Stagger
                def_queue.insert(0, def_die)
                rec = self.restore_stagger(def_unit, def_val)
                return f"Evade! Recycled & Recovered {rec} Stagger"

        return "Unknown interaction"

    def _resolve_onesided(self, queue, attacker, defender):
        log = []
        while queue:
            die = queue.pop(0)
            if defender.is_staggered():
                # По стаггеру бьем с полным уроном (можно добавить множитель x2)
                pass

            val = self.roll(die)
            if self.is_attack(die):
                dmg = self.apply_damage(defender, val, die.dtype)
                txt = f"Free Hit! {dmg} HP Dmg"
            else:
                txt = "Defensive die stored (Logic skipped for now)"

            log.append({"round": "One-Sided", "rolls": f"{die.dtype.value}({val})", "details": txt})
        return log