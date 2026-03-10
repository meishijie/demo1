import unittest

from unit_system import (
    Side,
    TerrainType,
    Unit,
    UnitType,
    can_unit_enter_tile,
    can_move_to,
    counter_multiplier,
    get_unit_stats,
    movement_cost,
    preview_combat,
    reachable_tiles,
    resolve_combat,
    terrain_defense_bonus,
)


class UnitSystemTests(unittest.TestCase):
    def test_gun_cavalry_archer_stats_exist(self) -> None:
        spear = get_unit_stats(UnitType.SPEAR)
        cavalry = get_unit_stats(UnitType.CAVALRY)
        archer = get_unit_stats(UnitType.ARCHER)

        self.assertGreater(spear.attack, 0)
        self.assertGreater(cavalry.movement, spear.movement)
        self.assertEqual(archer.min_range, 2)

    def test_counter_relationships(self) -> None:
        self.assertGreater(counter_multiplier(UnitType.SPEAR, UnitType.CAVALRY), 1.0)
        self.assertGreater(counter_multiplier(UnitType.CAVALRY, UnitType.ARCHER), 1.0)
        self.assertGreater(counter_multiplier(UnitType.ARCHER, UnitType.SPEAR), 1.0)
        self.assertLess(counter_multiplier(UnitType.CAVALRY, UnitType.SPEAR), 1.0)

    def test_forest_defense_bonus(self) -> None:
        attacker = Unit("p1", Side.PLAYER, UnitType.SPEAR, (1, 1))
        defender = Unit("e1", Side.ENEMY, UnitType.CAVALRY, (2, 1))

        plain = preview_combat(attacker, defender, TerrainType.PLAIN)
        forest = preview_combat(attacker, defender, TerrainType.FOREST)

        self.assertEqual(terrain_defense_bonus(TerrainType.FOREST), 2)
        self.assertGreater(plain.predicted_damage, forest.predicted_damage)

    def test_resolve_combat_enforces_minimum_damage_floor(self) -> None:
        attacker = Unit("p_arch", Side.PLAYER, UnitType.ARCHER, (1, 1))
        defender = Unit("e_cav", Side.ENEMY, UnitType.CAVALRY, (2, 1), hp=50)

        result = resolve_combat(attacker, defender, TerrainType.FOREST)

        self.assertEqual(result.predicted_damage, 1)
        self.assertEqual(result.defender_next_hp, 49)
        self.assertFalse(result.defender_defeated)

    def test_resolve_combat_marks_defeat_when_hp_reaches_zero(self) -> None:
        attacker = Unit("p_spear", Side.PLAYER, UnitType.SPEAR, (1, 1))
        defender = Unit("e_cav", Side.ENEMY, UnitType.CAVALRY, (2, 1), hp=10)

        result = resolve_combat(attacker, defender, TerrainType.PLAIN)

        self.assertEqual(result.predicted_damage, 18)
        self.assertEqual(result.defender_next_hp, 0)
        self.assertTrue(result.defender_defeated)

    def test_cavalry_forest_move_penalty(self) -> None:
        self.assertEqual(movement_cost(UnitType.CAVALRY, TerrainType.PLAIN), 1)
        self.assertEqual(movement_cost(UnitType.CAVALRY, TerrainType.FOREST), 2)
        self.assertEqual(movement_cost(UnitType.SPEAR, TerrainType.FOREST), 1)

    def test_can_unit_enter_tile_contract_with_river_and_sea(self) -> None:
        self.assertTrue(can_unit_enter_tile(terrain="plain", unit_type="spear"))
        self.assertFalse(can_unit_enter_tile(terrain="river", unit_type="spear"))
        self.assertFalse(can_unit_enter_tile(terrain="sea", unit_type="archer"))
        self.assertFalse(can_unit_enter_tile(terrain=TerrainType.RIVER, unit_type=UnitType.CAVALRY))

    def test_reachable_tiles_respects_impassable_river_and_sea(self) -> None:
        player = Unit("p1", Side.PLAYER, UnitType.SPEAR, (1, 1))
        units = [player]
        terrain_map = {
            (2, 1): TerrainType.RIVER,
            (1, 2): TerrainType.SEA,
        }

        result = reachable_tiles(player, units, terrain_map=terrain_map, map_width=4, map_height=4)
        self.assertNotIn((2, 1), result)
        self.assertNotIn((1, 2), result)

    def test_zoc_blocks_zoc_to_zoc_transition(self) -> None:
        player = Unit("p1", Side.PLAYER, UnitType.SPEAR, (1, 2))
        ally_blocker = Unit("p2", Side.PLAYER, UnitType.SPEAR, (1, 1))
        enemy = Unit("e1", Side.ENEMY, UnitType.SPEAR, (2, 2))
        units = [player, ally_blocker, enemy]

        result = reachable_tiles(player, units, terrain_map={}, map_width=5, map_height=5)
        self.assertNotIn((2, 1), result)
        self.assertFalse(can_move_to(player, (2, 1), units, {}, 5, 5))

    def test_enter_enemy_zoc_stops_further_expansion(self) -> None:
        player = Unit("p1", Side.PLAYER, UnitType.CAVALRY, (0, 0))
        enemy = Unit("e1", Side.ENEMY, UnitType.SPEAR, (3, 1))
        units = [player, enemy]

        result = reachable_tiles(player, units, terrain_map={}, map_width=6, map_height=3)
        self.assertIn((3, 0), result)
        self.assertNotIn((4, 0), result)


if __name__ == "__main__":
    unittest.main()
