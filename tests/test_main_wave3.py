import unittest

from main import ENEMY_COMMANDER_ID, PLAYER_COMMANDER_ID, Game, Terrain, manhattan_distance
from unit_system import Side, Unit, UnitType


def make_game(units: list[Unit], map_width: int = 10, map_height: int = 10) -> Game:
    game = Game.__new__(Game)
    game.map_width = map_width
    game.map_height = map_height
    game.terrain_map = [[Terrain.PLAIN for _ in range(map_width)] for _ in range(map_height)]
    game.terrain_lookup = {(x, y): "plain" for y in range(map_height) for x in range(map_width)}
    game.camera_x = 0.0
    game.camera_y = 0.0
    game.max_camera_x = 0.0
    game.max_camera_y = 0.0
    game.units = list(units)
    game.current_turn = Side.PLAYER
    game.acted_unit_ids = set()
    game.enemy_acted_unit_ids = set()
    game.selected_unit_id = None
    game.move_candidates = set()
    game.attack_candidates = set()
    game.hovered_unit_id = None
    game.enemy_turn_countdown = 0
    game.game_over = False
    game.winner_side = None
    game.status_text = ""
    return game


class MainWave3LogicTests(unittest.TestCase):
    def test_enemy_turn_attacks_when_target_in_range(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 1), hp=100),
            Unit(ENEMY_COMMANDER_ID, Side.ENEMY, UnitType.SPEAR, (1, 1), hp=100),
        ]
        game = make_game(units)
        game.current_turn = Side.ENEMY

        game._update_enemy_turn()

        player_lord = game._unit_by_id(PLAYER_COMMANDER_ID)
        self.assertIsNotNone(player_lord)
        self.assertLess(player_lord.hp, 100)
        self.assertIn(ENEMY_COMMANDER_ID, game.enemy_acted_unit_ids)

    def test_enemy_turn_moves_toward_target_when_no_attack(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (7, 0), hp=100),
            Unit("e_cav", Side.ENEMY, UnitType.CAVALRY, (0, 0), hp=100),
            Unit(ENEMY_COMMANDER_ID, Side.ENEMY, UnitType.SPEAR, (0, 7), hp=100),
        ]
        game = make_game(units)
        game.current_turn = Side.ENEMY
        game.enemy_acted_unit_ids.add(ENEMY_COMMANDER_ID)

        before = game._unit_by_id("e_cav")
        self.assertIsNotNone(before)
        before_pos = before.position

        game._update_enemy_turn()

        after = game._unit_by_id("e_cav")
        self.assertIsNotNone(after)
        self.assertNotEqual(before_pos, after.position)
        self.assertLess(manhattan_distance(after.position, (7, 0)), manhattan_distance(before_pos, (7, 0)))

    def test_enemy_turn_switches_back_to_player_after_all_enemy_actions(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (9, 9), hp=100),
            Unit(ENEMY_COMMANDER_ID, Side.ENEMY, UnitType.SPEAR, (0, 0), hp=100),
        ]
        game = make_game(units)
        game.current_turn = Side.ENEMY
        game.acted_unit_ids = {PLAYER_COMMANDER_ID}

        game._update_enemy_turn()
        self.assertEqual(game.current_turn, Side.ENEMY)
        self.assertIn(ENEMY_COMMANDER_ID, game.enemy_acted_unit_ids)

        game.enemy_turn_countdown = 0
        game._update_enemy_turn()

        self.assertEqual(game.current_turn, Side.PLAYER)
        self.assertEqual(game.acted_unit_ids, set())
        self.assertEqual(game.enemy_acted_unit_ids, set())

    def test_player_defeats_enemy_commander_triggers_victory(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (1, 1), hp=100),
            Unit(ENEMY_COMMANDER_ID, Side.ENEMY, UnitType.SPEAR, (2, 1), hp=1),
        ]
        game = make_game(units)
        game.current_turn = Side.PLAYER

        attacker = game._unit_by_id(PLAYER_COMMANDER_ID)
        defender = game._unit_by_id(ENEMY_COMMANDER_ID)
        self.assertIsNotNone(attacker)
        self.assertIsNotNone(defender)

        game._execute_attack(attacker, defender)

        self.assertTrue(game.game_over)
        self.assertEqual(game.winner_side, Side.PLAYER)
        self.assertIsNone(game._unit_by_id(ENEMY_COMMANDER_ID))

    def test_enemy_defeats_player_commander_triggers_defeat(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 1), hp=1),
            Unit(ENEMY_COMMANDER_ID, Side.ENEMY, UnitType.SPEAR, (1, 1), hp=100),
        ]
        game = make_game(units)
        game.current_turn = Side.ENEMY

        game._update_enemy_turn()

        self.assertTrue(game.game_over)
        self.assertEqual(game.winner_side, Side.ENEMY)
        self.assertIsNone(game._unit_by_id(PLAYER_COMMANDER_ID))


if __name__ == "__main__":
    unittest.main()
