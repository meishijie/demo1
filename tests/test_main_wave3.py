import unittest
from unittest import mock

import main as main_module
from main import ENEMY_COMMANDER_ID, PLAYER_COMMANDER_ID, Game, Terrain, manhattan_distance
from unit_system import Side, Unit, UnitType


class _FakePyxelInput:
    MOUSE_BUTTON_LEFT = 0
    MOUSE_BUTTON_RIGHT = 1

    def __init__(self) -> None:
        self.mouse_x = 0
        self.mouse_y = 0
        self._pressed_buttons: set[int] = set()

    def btnp(self, key: int) -> bool:
        return key in self._pressed_buttons

    def rect(self, *_args, **_kwargs) -> None:
        return None

    def rectb(self, *_args, **_kwargs) -> None:
        return None


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
    game.combat_effects = []
    game.floating_texts = []
    return game


class MainWave3LogicTests(unittest.TestCase):
    def _left_click_tile(self, game: Game, fake_pyxel: _FakePyxelInput, tile: tuple[int, int]) -> None:
        fake_pyxel.mouse_x = tile[0] * main_module.TILE_SIZE + main_module.TILE_SIZE // 2
        fake_pyxel.mouse_y = tile[1] * main_module.TILE_SIZE + main_module.TILE_SIZE // 2
        fake_pyxel._pressed_buttons = {fake_pyxel.MOUSE_BUTTON_LEFT}
        game._handle_player_input()
        fake_pyxel._pressed_buttons.clear()

    def test_enemy_turn_attacks_when_target_in_range(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 1), hp=100),
            Unit(ENEMY_COMMANDER_ID, Side.ENEMY, UnitType.SPEAR, (1, 1), hp=100),
        ]
        game = make_game(units)
        game.current_turn = Side.ENEMY
        enemy_before = game._unit_by_id(ENEMY_COMMANDER_ID)
        self.assertIsNotNone(enemy_before)
        enemy_before_pos = enemy_before.position

        game._update_enemy_turn()

        player_lord = game._unit_by_id(PLAYER_COMMANDER_ID)
        enemy_after = game._unit_by_id(ENEMY_COMMANDER_ID)
        self.assertIsNotNone(player_lord)
        self.assertIsNotNone(enemy_after)
        self.assertLess(player_lord.hp, 100)
        self.assertEqual(enemy_after.position, enemy_before_pos)
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

    def test_enemy_multi_turn_flow_no_stall_and_no_duplicate_attack_in_phase(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (2, 1), hp=100),
            Unit(ENEMY_COMMANDER_ID, Side.ENEMY, UnitType.SPEAR, (1, 1), hp=100),
        ]
        game = make_game(units)
        game.current_turn = Side.PLAYER

        for _ in range(3):
            player_before_phase = game._unit_by_id(PLAYER_COMMANDER_ID)
            self.assertIsNotNone(player_before_phase)
            hp_before_phase = player_before_phase.hp

            game._switch_to_enemy_turn(manual=True)
            guard = 0
            while game.current_turn == Side.ENEMY and not game.game_over:
                guard += 1
                self.assertLessEqual(guard, 2, "enemy phase should finish without stalling")
                game.enemy_turn_countdown = 0
                game._update_enemy_turn()

            player_after_phase = game._unit_by_id(PLAYER_COMMANDER_ID)
            self.assertIsNotNone(player_after_phase)
            self.assertEqual(game.current_turn, Side.PLAYER)
            self.assertEqual(player_after_phase.hp, hp_before_phase - 10)
            self.assertFalse(game.game_over)

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

    def test_player_input_attack_updates_hp_and_switches_turn(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (1, 1), hp=100),
            Unit(ENEMY_COMMANDER_ID, Side.ENEMY, UnitType.SPEAR, (2, 1), hp=100),
        ]
        game = make_game(units)
        fake_pyxel = _FakePyxelInput()

        with mock.patch.object(main_module, "pyxel", fake_pyxel):
            self._left_click_tile(game, fake_pyxel, (1, 1))
            self.assertEqual(game.selected_unit_id, PLAYER_COMMANDER_ID)
            self.assertIn((2, 1), game.attack_candidates)

            self._left_click_tile(game, fake_pyxel, (2, 1))

        defender = game._unit_by_id(ENEMY_COMMANDER_ID)
        self.assertIsNotNone(defender)
        self.assertEqual(defender.hp, 90)
        self.assertIn(PLAYER_COMMANDER_ID, game.acted_unit_ids)
        self.assertEqual(game.current_turn, Side.ENEMY)

    def test_acted_player_unit_cannot_attack_twice_in_same_turn(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (1, 1), hp=100),
            Unit("p_arch", Side.PLAYER, UnitType.ARCHER, (0, 0), hp=100),
            Unit(ENEMY_COMMANDER_ID, Side.ENEMY, UnitType.SPEAR, (2, 1), hp=100),
        ]
        game = make_game(units)
        fake_pyxel = _FakePyxelInput()

        with mock.patch.object(main_module, "pyxel", fake_pyxel):
            self._left_click_tile(game, fake_pyxel, (1, 1))
            self._left_click_tile(game, fake_pyxel, (2, 1))
            defender_after_first_attack = game._unit_by_id(ENEMY_COMMANDER_ID)
            self.assertIsNotNone(defender_after_first_attack)
            hp_after_first_attack = defender_after_first_attack.hp

            self._left_click_tile(game, fake_pyxel, (1, 1))
            self._left_click_tile(game, fake_pyxel, (2, 1))

        defender_after_retry = game._unit_by_id(ENEMY_COMMANDER_ID)
        self.assertIsNotNone(defender_after_retry)
        self.assertEqual(defender_after_retry.hp, hp_after_first_attack)
        self.assertIn(PLAYER_COMMANDER_ID, game.acted_unit_ids)
        self.assertEqual(game.current_turn, Side.PLAYER)

    def test_hovered_enemy_reflects_post_attack_hp(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (1, 1), hp=100),
            Unit(ENEMY_COMMANDER_ID, Side.ENEMY, UnitType.SPEAR, (2, 1), hp=100),
        ]
        game = make_game(units)
        game.hovered_unit_id = ENEMY_COMMANDER_ID

        attacker = game._unit_by_id(PLAYER_COMMANDER_ID)
        defender = game._unit_by_id(ENEMY_COMMANDER_ID)
        self.assertIsNotNone(attacker)
        self.assertIsNotNone(defender)

        game._execute_attack(attacker, defender)

        hovered_enemy = game._unit_by_id(game.hovered_unit_id)
        self.assertIsNotNone(hovered_enemy)
        self.assertEqual(hovered_enemy.hp, 90)

    def test_edge_scroll_respects_viewport_edges_and_clamps_camera(self) -> None:
        units = [Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (1, 1), hp=100)]
        game = make_game(units, map_width=40, map_height=40)
        game.max_camera_x = 100.0
        game.max_camera_y = 80.0
        fake_pyxel = _FakePyxelInput()

        with mock.patch.object(main_module, "pyxel", fake_pyxel):
            fake_pyxel.mouse_x = -1
            fake_pyxel.mouse_y = -1
            game._update_edge_scroll()
            self.assertEqual(game.camera_x, 0.0)
            self.assertEqual(game.camera_y, 0.0)

            fake_pyxel.mouse_x = main_module.EDGE_SCROLL_MARGIN - 1
            fake_pyxel.mouse_y = main_module.EDGE_SCROLL_MARGIN - 1
            game._update_edge_scroll()
            self.assertEqual(game.camera_x, 0.0)
            self.assertEqual(game.camera_y, 0.0)

            game.camera_x = 99.0
            game.camera_y = 79.0
            fake_pyxel.mouse_x = main_module.SCREEN_WIDTH - 1
            fake_pyxel.mouse_y = main_module.SCREEN_HEIGHT - 1
            game._update_edge_scroll()
            self.assertEqual(game.camera_x, game.max_camera_x)
            self.assertEqual(game.camera_y, game.max_camera_y)

    def test_hover_info_uses_compact_layout_near_bottom_bar(self) -> None:
        units = [
            Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (1, 1), hp=100),
            Unit(ENEMY_COMMANDER_ID, Side.ENEMY, UnitType.SPEAR, (2, 1), hp=100),
        ]
        game = make_game(units)
        game.hovered_unit_id = ENEMY_COMMANDER_ID
        fake_pyxel = _FakePyxelInput()
        fake_pyxel.mouse_x = 120
        fake_pyxel.mouse_y = main_module.SCREEN_HEIGHT - main_module.BOTTOM_BAR_HEIGHT - 1

        with mock.patch.object(main_module, "pyxel", fake_pyxel):
            with mock.patch.object(game, "_draw_text") as draw_text:
                game._draw_hover_unit_info()

        self.assertEqual(draw_text.call_count, 8)

    def test_choose_font_prefers_default_for_cjk_and_compact_for_ascii(self) -> None:
        units = [Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (1, 1), hp=100)]
        game = make_game(units)
        default_font = object()
        compact_font = object()
        game.default_font = default_font
        game.compact_font = compact_font

        self.assertIs(game._choose_font("阵营: 玩家", compact=True), default_font)
        self.assertIs(game._choose_font("TURN: PLAYER", compact=True), compact_font)
        self.assertIs(game._choose_font("TURN: PLAYER", compact=False), default_font)

    def test_choose_font_compact_ascii_falls_back_to_pyxel_default_when_unavailable(self) -> None:
        units = [Unit(PLAYER_COMMANDER_ID, Side.PLAYER, UnitType.SPEAR, (1, 1), hp=100)]
        game = make_game(units)
        game.default_font = None
        game.compact_font = None

        self.assertIsNone(game._choose_font("TURN: PLAYER", compact=True))


if __name__ == "__main__":
    unittest.main()
