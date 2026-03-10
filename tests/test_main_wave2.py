import unittest

from main import attackable_enemy_positions, has_unacted_units
from unit_system import Side, Unit, UnitType


class MainWave2LogicTests(unittest.TestCase):
    def test_archer_attack_candidates_respect_range_and_side(self) -> None:
        attacker = Unit("p_arch", Side.PLAYER, UnitType.ARCHER, (3, 3))
        enemy_in_range = Unit("e_in", Side.ENEMY, UnitType.SPEAR, (5, 3))  # distance 2
        enemy_too_close = Unit("e_close", Side.ENEMY, UnitType.SPEAR, (4, 3))  # distance 1
        enemy_too_far = Unit("e_far", Side.ENEMY, UnitType.CAVALRY, (8, 3))  # distance 5
        ally = Unit("p_ally", Side.PLAYER, UnitType.SPEAR, (6, 3))

        result = attackable_enemy_positions(
            attacker,
            [attacker, enemy_in_range, enemy_too_close, enemy_too_far, ally],
        )

        self.assertIn((5, 3), result)
        self.assertNotIn((4, 3), result)
        self.assertNotIn((8, 3), result)
        self.assertNotIn((6, 3), result)

    def test_has_unacted_units_only_counts_target_side(self) -> None:
        units = [
            Unit("p1", Side.PLAYER, UnitType.SPEAR, (1, 1)),
            Unit("p2", Side.PLAYER, UnitType.CAVALRY, (2, 1)),
            Unit("e1", Side.ENEMY, UnitType.ARCHER, (3, 1)),
        ]

        self.assertTrue(has_unacted_units(units, Side.PLAYER, {"p1"}))
        self.assertFalse(has_unacted_units(units, Side.PLAYER, {"p1", "p2"}))
        self.assertTrue(has_unacted_units(units, Side.ENEMY, set()))


if __name__ == "__main__":
    unittest.main()
