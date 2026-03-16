import copy
import unittest
from unittest.mock import MagicMock
import sys

sys.modules['pyxel'] = MagicMock()

from main import ENEMY_COMMANDER_ID, PLAYER_COMMANDER_ID, Game, Terrain
from unit_system import Side, Unit, UnitType


def make_game_for_rewind(
    units: list[Unit], map_width: int = 10, map_height: int = 10
) -> Game:
    game = Game.__new__(Game)
    game.map_width = map_width
    game.map_height = map_height
    game.terrain_map = [
        [Terrain.PLAIN for _ in range(map_width)] for _ in range(map_height)
    ]
    game.terrain_lookup = {
        (x, y): "plain" for y in range(map_height) for x in range(map_width)
    }
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
    game.score = 0
    game.wave = 1
    game.effects = []
    game.particles = []
    game.shake_x = 0
    game.shake_y = 0
    game.shake_duration = 0
    game.animating = False
    game.combat_queue = []
    game.move_queue = []
    game.hit_stop_frames = 0
    game.glitch_frames = 0
    game.history = []
    game.combat_timer = 0
    game.unit_offsets = {}
    return game


class RewindTests(unittest.TestCase):
    def test_rewind_restores_unit_positions(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
            Unit(ENEMY_COMMANDER_ID, Side.ENEMY, UnitType.SPEAR, (5, 5), hp=100),
        ]
        game = make_game_for_rewind(units)

        original_position = (2, 2)
        game._save_state()

        game.units[0] = Unit(
            PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (4, 4), hp=100
        )
        self.assertEqual(game.units[0].position, (4, 4))

        game._rewind_time()

        restored_unit = game._unit_by_id(PLAYER_COMMANDER_ID)
        self.assertIsNotNone(restored_unit)
        self.assertEqual(restored_unit.position, original_position)

    def test_rewind_restores_unit_hp(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
            Unit(ENEMY_COMMANDER_ID, Side.ENEMY, UnitType.SPEAR, (5, 5), hp=100),
        ]
        game = make_game_for_rewind(units)

        game._save_state()

        game.units[0] = Unit(
            PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=50
        )
        self.assertEqual(game.units[0].hp, 50)

        game._rewind_time()

        restored_unit = game._unit_by_id(PLAYER_COMMANDER_ID)
        self.assertIsNotNone(restored_unit)
        self.assertEqual(restored_unit.hp, 100)

    def test_rewind_restores_terrain_changes(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
        ]
        game = make_game_for_rewind(units)

        game._save_state()

        game.terrain_map[2][2] = Terrain.FIRE
        game.terrain_lookup[(2, 2)] = "fire"
        self.assertEqual(game.terrain_map[2][2], Terrain.FIRE)

        game._rewind_time()

        self.assertEqual(game.terrain_map[2][2], Terrain.PLAIN)
        self.assertEqual(game.terrain_lookup[(2, 2)], "plain")

    def test_rewind_restores_score(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
        ]
        game = make_game_for_rewind(units)

        game.score = 100
        game._save_state()

        game.score = 200
        self.assertEqual(game.score, 200)

        game._rewind_time()

        self.assertEqual(game.score, 100)

    def test_rewind_restores_wave(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
        ]
        game = make_game_for_rewind(units)

        game.wave = 1
        game._save_state()

        game.wave = 2
        self.assertEqual(game.wave, 2)

        game._rewind_time()

        self.assertEqual(game.wave, 1)

    def test_rewind_restores_acted_unit_ids(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
            Unit("p2", Side.PLAYER, UnitType.CAVALRY, (3, 3), hp=100),
        ]
        game = make_game_for_rewind(units)

        game._save_state()
        game.acted_unit_ids = {PLAYER_COMMANDER_ID, "p2"}
        self.assertEqual(len(game.acted_unit_ids), 2)

        game._rewind_time()

        self.assertEqual(len(game.acted_unit_ids), 0)

    def test_rewind_returns_to_player_turn(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
        ]
        game = make_game_for_rewind(units)

        game._save_state()

        game.current_turn = Side.ENEMY

        game._rewind_time()

        self.assertEqual(game.current_turn, Side.PLAYER)

    def test_rewind_clears_enemy_acted_unit_ids(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
        ]
        game = make_game_for_rewind(units)

        game._save_state()
        game.enemy_acted_unit_ids = {ENEMY_COMMANDER_ID}
        self.assertEqual(len(game.enemy_acted_unit_ids), 1)

        game._rewind_time()

        self.assertEqual(len(game.enemy_acted_unit_ids), 0)

    def test_rewind_clears_selection(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
        ]
        game = make_game_for_rewind(units)

        game._save_state()
        game.selected_unit_id = PLAYER_COMMANDER_ID
        game.move_candidates = {(3, 3), (4, 4)}
        game.attack_candidates = {(5, 5)}

        game._rewind_time()

        self.assertIsNone(game.selected_unit_id)
        self.assertEqual(len(game.move_candidates), 0)
        self.assertEqual(len(game.attack_candidates), 0)

    def test_rewind_with_no_history_does_nothing(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
        ]
        game = make_game_for_rewind(units)

        self.assertEqual(len(game.history), 0)

        game._rewind_time()

        self.assertEqual(len(game.history), 0)

    def test_rewind_resets_winner_to_none(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
        ]
        game = make_game_for_rewind(units)

        game._save_state()
        game.winner_side = Side.ENEMY

        game._rewind_time()

        self.assertIsNone(game.winner_side)

    def test_rewind_resets_enemy_turn_countdown(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
        ]
        game = make_game_for_rewind(units)

        game._save_state()
        game.enemy_turn_countdown = 30

        game._rewind_time()

        self.assertEqual(game.enemy_turn_countdown, 0)

    def test_rewind_sets_success_status_message(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
        ]
        game = make_game_for_rewind(units)

        game._save_state()

        game._rewind_time()

        self.assertEqual(game.status_text, "Time rewound! Player turn.")

    def test_rewind_sets_glitch_frames_for_visual_feedback(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
        ]
        game = make_game_for_rewind(units)

        game._save_state()

        game._rewind_time()

        self.assertEqual(game.glitch_frames, 30)

    def test_rewind_with_single_history_state(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
        ]
        game = make_game_for_rewind(units)

        game._save_state()
        original_position = game.units[0].position

        game.units[0] = Unit(
            PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (5, 5), hp=50
        )

        game._rewind_time()

        restored_unit = game._unit_by_id(PLAYER_COMMANDER_ID)
        self.assertIsNotNone(restored_unit)
        self.assertEqual(restored_unit.position, original_position)

    def test_history_limit_is_enforced(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 2), hp=100),
        ]
        game = make_game_for_rewind(units)

        for i in range(15):
            game._save_state()

        self.assertEqual(len(game.history), 10)


if __name__ == "__main__":
    unittest.main()
