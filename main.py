from __future__ import annotations

import os
import random
from dataclasses import replace
from enum import IntEnum
from typing import Iterable

import pyxel

try:
    import unit_system
except Exception:
    unit_system = None


SCREEN_WIDTH = 320
SCREEN_HEIGHT = 192
TILE_SIZE = 16

VISIBLE_TILES_X = SCREEN_WIDTH // TILE_SIZE  # 20
VISIBLE_TILES_Y = SCREEN_HEIGHT // TILE_SIZE  # 12

MAP_WIDTH = 40
MAP_HEIGHT = 40

EDGE_SCROLL_MARGIN = 12
SCROLL_SPEED = 2.6
ENEMY_TURN_DELAY_FRAMES = 26

TOP_BAR_HEIGHT = 18
BOTTOM_BAR_HEIGHT = 14
END_TURN_BUTTON = (SCREEN_WIDTH - 76, 3, 70, 12)
PLAYER_COMMANDER_ID = "p_lord"
ENEMY_COMMANDER_ID = "e_lord"


class GameState(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


class Terrain(IntEnum):
    PLAIN = 0
    FOREST = 1
    RIVER = 2
    SEA = 3
    FIRE = 4


TERRAIN_COLOR = {
    Terrain.PLAIN: 3,
    Terrain.FOREST: 11,
    Terrain.RIVER: 12,
    Terrain.SEA: 1,
    Terrain.FIRE: 9,
}

IMPASSABLE_TERRAIN = {Terrain.RIVER, Terrain.SEA}


def is_terrain_passable(terrain: Terrain) -> bool:
    return terrain not in IMPASSABLE_TERRAIN


def can_unit_enter_tile(terrain: Terrain, unit_type: str | None = None) -> bool:
    """Integration hook for the unit module; map-layer rules stay as fallback."""
    if not is_terrain_passable(terrain):
        return False

    if unit_system and hasattr(unit_system, "can_unit_enter_tile"):
        return bool(unit_system.can_unit_enter_tile(terrain.name.lower(), unit_type))
    return True


def manhattan_distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def attackable_enemy_positions(attacker: "unit_system.Unit", units: Iterable["unit_system.Unit"]) -> set[tuple[int, int]]:
    if unit_system is None:
        return set()

    stats = unit_system.get_unit_stats(attacker.unit_type)
    targets: set[tuple[int, int]] = set()
    for unit in units:
        if unit.side == attacker.side:
            continue
        distance = manhattan_distance(attacker.position, unit.position)
        if stats.min_range <= distance <= stats.max_range:
            targets.add(unit.position)
    return targets


def has_unacted_units(
    units: Iterable["unit_system.Unit"],
    side: "unit_system.Side",
    acted_unit_ids: set[str],
) -> bool:
    return any(unit.side == side and unit.unit_id not in acted_unit_ids and unit.hp > 0 for unit in units)


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _font_search_paths(filename: str) -> list[str]:
    paths = [
        filename,
        os.path.join("assets", filename),
    ]
    try:
        pyxel_root = os.path.dirname(pyxel.__file__)
        paths.append(os.path.join(pyxel_root, "examples", "assets", filename))
    except Exception:
        pass
    return paths


def _generate_map(width: int, height: int) -> list[list[Terrain]]:
    random.seed(7)
    terrain = [[Terrain.PLAIN for _ in range(width)] for _ in range(height)]

    # Sea belts so the player can quickly verify deep-water areas.
    for y in range(height):
        for x in range(width):
            if y <= 2 or x >= width - 5:
                terrain[y][x] = Terrain.SEA

    # Meandering river across the map center.
    river_y = height // 2
    for x in range(width):
        river_y += random.choice((-1, 0, 0, 1))
        river_y = max(4, min(height - 5, river_y))
        terrain[river_y][x] = Terrain.RIVER
        if x % 5 == 0 and river_y + 1 < height:
            terrain[river_y + 1][x] = Terrain.RIVER

    # Forest patches in passable land.
    for _ in range(22):
        center_x = random.randint(2, width - 8)
        center_y = random.randint(4, height - 4)
        radius = random.randint(1, 2)
        for oy in range(-radius, radius + 1):
            for ox in range(-radius, radius + 1):
                tx = center_x + ox
                ty = center_y + oy
                if 0 <= tx < width and 0 <= ty < height and terrain[ty][tx] == Terrain.PLAIN:
                    if random.random() > 0.2:
                        terrain[ty][tx] = Terrain.FOREST

    return terrain


class Game:
    def __init__(self) -> None:
        if unit_system is None:
            raise RuntimeError("unit_system is required for Wave 2 gameplay")

        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Pyxel SRPG Prototype", fps=30)
        pyxel.mouse(True)

        self.map_width = MAP_WIDTH
        self.map_height = MAP_HEIGHT
        self.terrain_map = _generate_map(self.map_width, self.map_height)
        self.terrain_lookup = self._build_terrain_lookup()

        self.camera_x = 0.0
        self.camera_y = 0.0

        self.max_camera_x = max(0, self.map_width * TILE_SIZE - SCREEN_WIDTH)
        self.max_camera_y = max(0, self.map_height * TILE_SIZE - SCREEN_HEIGHT)

        self.units = self._create_initial_units()
        self.current_turn = unit_system.Side.PLAYER
        self.acted_unit_ids: set[str] = set()
        self.enemy_acted_unit_ids: set[str] = set()

        self.selected_unit_id: str | None = None
        self.move_candidates: set[tuple[int, int]] = set()
        self.attack_candidates: set[tuple[int, int]] = set()

        self.hovered_unit_id: str | None = None
        self.enemy_turn_countdown = 0
        self.game_over = False
        self.winner_side: unit_system.Side | None = None
        self.status_text = "Player turn: choose a unit"

        self.game_state = GameState.TITLE
        self.title_frame = 0

        self.default_font, self.compact_font = self._load_fonts()

        self.combat_effects: list[dict] = []
        self.floating_texts: list[dict] = []

        pyxel.run(self.update, self.draw)

    def _load_fonts(self) -> tuple[pyxel.Font | None, pyxel.Font | None]:
        default_font = self._try_load_font("umplus_j12r.bdf")
        compact_font = self._try_load_font("misaki_gothic.bdf")
        return default_font, compact_font

    def _try_load_font(self, filename: str) -> pyxel.Font | None:
        for path in _font_search_paths(filename):
            if not os.path.exists(path):
                continue
            try:
                return pyxel.Font(path)
            except Exception:
                continue
        return None

    def _choose_font(self, text: str, compact: bool = False) -> pyxel.Font | None:
        has_cjk = _contains_cjk(text)
        if has_cjk and self.default_font:
            return self.default_font
        if compact:
            if self.compact_font and not has_cjk:
                return self.compact_font
            if not has_cjk:
                return None
        return self.default_font or self.compact_font

    def _draw_text(self, x: int, y: int, text: str, color: int, compact: bool = False) -> None:
        pyxel.text(x, y, text, color, self._choose_font(text, compact=compact))

    def _draw_text_shadowed(self, x: int, y: int, text: str, color: int, shadow_color: int = 0, compact: bool = False) -> None:
        try:
            self._draw_text(x + 1, y + 1, text, shadow_color, compact)
        except Exception:
            pass
        self._draw_text(x, y, text, color, compact)

    def _create_initial_units(self) -> list["unit_system.Unit"]:
        return [
            unit_system.Unit("p_lord", unit_system.Side.PLAYER, unit_system.UnitType.SPEAR, (4, 6), hp=100),
            unit_system.Unit("p_cav", unit_system.Side.PLAYER, unit_system.UnitType.CAVALRY, (3, 8), hp=100),
            unit_system.Unit("p_arch", unit_system.Side.PLAYER, unit_system.UnitType.ARCHER, (6, 8), hp=100),
            unit_system.Unit("e_lord", unit_system.Side.ENEMY, unit_system.UnitType.SPEAR, (12, 7), hp=100),
            unit_system.Unit("e_cav", unit_system.Side.ENEMY, unit_system.UnitType.CAVALRY, (13, 9), hp=100),
            unit_system.Unit("e_arch", unit_system.Side.ENEMY, unit_system.UnitType.ARCHER, (15, 6), hp=100),
        ]

    def _build_terrain_lookup(self) -> dict[tuple[int, int], str]:
        lookup: dict[tuple[int, int], str] = {}
        for y, row in enumerate(self.terrain_map):
            for x, terrain in enumerate(row):
                lookup[(x, y)] = terrain.name.lower()
        return lookup

    def update(self) -> None:
        if self.game_state == GameState.TITLE:
            self.title_frame += 1
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
                self.game_state = GameState.PLAYING
            return

        if self.game_over:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
                self._restart_game()
            return

        self._update_combat_effects()
        self._update_edge_scroll()
        self._update_hovered_unit()
        if self.game_over or self._check_battle_end():
            return

        if self.current_turn == unit_system.Side.ENEMY:
            self._update_enemy_turn()
            return

        self._handle_player_input()

    def _restart_game(self) -> None:
        self.units = self._create_initial_units()
        self.current_turn = unit_system.Side.PLAYER
        self.acted_unit_ids.clear()
        self.enemy_acted_unit_ids.clear()
        self.selected_unit_id = None
        self.move_candidates.clear()
        self.attack_candidates.clear()
        self.hovered_unit_id = None
        self.enemy_turn_countdown = 0
        self.game_over = False
        self.winner_side = None
        self.status_text = "Player turn: choose a unit"
        self.combat_effects.clear()
        self.floating_texts.clear()
        self.camera_x = 0.0
        self.camera_y = 0.0

    def _update_combat_effects(self) -> None:
        for effect in self.combat_effects[:]:
            effect["frames_remaining"] -= 1
            if effect["frames_remaining"] <= 0:
                self.combat_effects.remove(effect)

        for ft in self.floating_texts[:]:
            ft["frames_remaining"] -= 1
            ft["y"] -= 0.5
            if ft["frames_remaining"] <= 0:
                self.floating_texts.remove(ft)

    def _update_enemy_turn(self) -> None:
        if self.enemy_turn_countdown > 0:
            self.enemy_turn_countdown -= 1
            return

        enemy_unit = self._next_unacted_enemy_unit()
        if enemy_unit is None:
            self._start_player_turn()
            return

        if not self._enemy_try_attack(enemy_unit):
            self._enemy_try_advance(enemy_unit)

        self.enemy_acted_unit_ids.add(enemy_unit.unit_id)
        if self._check_battle_end():
            return
        self.enemy_turn_countdown = max(1, ENEMY_TURN_DELAY_FRAMES // 3)

    def _start_player_turn(self) -> None:
        self.current_turn = unit_system.Side.PLAYER
        self.acted_unit_ids.clear()
        self.enemy_acted_unit_ids.clear()
        self.status_text = "Player turn: choose a unit"

    def _next_unacted_enemy_unit(self) -> "unit_system.Unit | None":
        for unit in self.units:
            if unit.side != unit_system.Side.ENEMY:
                continue
            if unit.unit_id in self.enemy_acted_unit_ids or unit.hp <= 0:
                continue
            return unit
        return None

    def _enemy_try_attack(self, enemy_unit: "unit_system.Unit") -> bool:
        attack_tiles = attackable_enemy_positions(enemy_unit, self.units)
        if not attack_tiles:
            return False

        targets = [
            unit
            for unit in self.units
            if unit.side == unit_system.Side.PLAYER and unit.position in attack_tiles and unit.hp > 0
        ]
        if not targets:
            return False

        target = min(
            targets,
            key=lambda unit: (
                unit.unit_id != PLAYER_COMMANDER_ID,
                unit.hp,
                manhattan_distance(enemy_unit.position, unit.position),
            ),
        )
        self._apply_attack(enemy_unit, target)
        return True

    def _enemy_try_advance(self, enemy_unit: "unit_system.Unit") -> bool:
        target = self._select_enemy_target(enemy_unit)
        if target is None:
            self.status_text = f"{enemy_unit.unit_id} holds position"
            return False

        reachable = unit_system.reachable_tiles(
            unit=enemy_unit,
            units=self.units,
            terrain_map=self.terrain_lookup,
            map_width=self.map_width,
            map_height=self.map_height,
        )
        if not reachable:
            self.status_text = f"{enemy_unit.unit_id} holds position"
            return False

        current_distance = manhattan_distance(enemy_unit.position, target.position)
        best_tile = min(
            reachable,
            key=lambda tile: (
                manhattan_distance(tile, target.position),
                manhattan_distance(tile, enemy_unit.position),
                tile[1],
                tile[0],
            ),
        )
        if manhattan_distance(best_tile, target.position) >= current_distance:
            self.status_text = f"{enemy_unit.unit_id} holds position"
            return False

        self._replace_unit(replace(enemy_unit, position=best_tile))
        self.status_text = f"{enemy_unit.unit_id} advanced to {best_tile}"
        return True

    def _select_enemy_target(self, enemy_unit: "unit_system.Unit") -> "unit_system.Unit | None":
        player_units = [unit for unit in self.units if unit.side == unit_system.Side.PLAYER and unit.hp > 0]
        if not player_units:
            return None
        return min(
            player_units,
            key=lambda unit: (
                unit.unit_id != PLAYER_COMMANDER_ID,
                manhattan_distance(enemy_unit.position, unit.position),
                unit.hp,
            ),
        )

    def _handle_player_input(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            self._clear_selection()

        if not pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            return

        if self._is_mouse_on_end_turn_button(pyxel.mouse_x, pyxel.mouse_y):
            self._switch_to_enemy_turn(manual=True)
            return

        clicked_tile = self._screen_to_map_tile(pyxel.mouse_x, pyxel.mouse_y)
        if clicked_tile is None:
            self._clear_selection()
            return

        clicked_unit = self._unit_at(clicked_tile)
        selected_unit = self._unit_by_id(self.selected_unit_id)

        if selected_unit and clicked_tile in self.move_candidates:
            self._execute_move(selected_unit, clicked_tile)
            return

        if (
            selected_unit
            and clicked_tile in self.attack_candidates
            and clicked_unit
            and clicked_unit.side != selected_unit.side
        ):
            self._execute_attack(selected_unit, clicked_unit)
            return

        if (
            clicked_unit
            and clicked_unit.side == unit_system.Side.PLAYER
            and clicked_unit.unit_id not in self.acted_unit_ids
        ):
            self._select_unit(clicked_unit)
            return

        self._clear_selection()

    def _select_unit(self, unit: "unit_system.Unit") -> None:
        self.selected_unit_id = unit.unit_id
        self.move_candidates = unit_system.reachable_tiles(
            unit=unit,
            units=self.units,
            terrain_map=self.terrain_lookup,
            map_width=self.map_width,
            map_height=self.map_height,
        )
        self.attack_candidates = attackable_enemy_positions(unit, self.units)
        self.status_text = f"{unit.unit_id}: choose move or attack"

    def _execute_move(self, unit: "unit_system.Unit", target: tuple[int, int]) -> None:
        self._replace_unit(replace(unit, position=target))
        self.acted_unit_ids.add(unit.unit_id)
        self.status_text = f"{unit.unit_id} moved to {target}"
        self._clear_selection()
        self._auto_switch_turn_if_needed()

    def _execute_attack(self, attacker: "unit_system.Unit", defender: "unit_system.Unit") -> None:
        self._apply_attack(attacker, defender)
        self.acted_unit_ids.add(attacker.unit_id)
        self._clear_selection()
        if self._check_battle_end():
            return
        self._auto_switch_turn_if_needed()

    def _apply_attack(self, attacker: "unit_system.Unit", defender: "unit_system.Unit") -> None:
        defender_terrain = unit_system.TerrainType(
            self.terrain_map[defender.position[1]][defender.position[0]].name.lower()
        )
        resolution = unit_system.resolve_combat(attacker, defender, defender_terrain)

        self.combat_effects.append({
            "type": "attack_flash",
            "target_pos": defender.position,
            "frames_remaining": 5,
        })

        self.floating_texts.append({
            "text": f"-{resolution.predicted_damage}",
            "x": defender.position[0] * TILE_SIZE + TILE_SIZE // 2,
            "y": defender.position[1] * TILE_SIZE,
            "frames_remaining": 30,
            "color": 9,
        })

        if resolution.defender_defeated:
            self._remove_unit(defender.unit_id)
            self.combat_effects.append({
                "type": "defeat_burst",
                "target_pos": defender.position,
                "frames_remaining": 20,
            })
            self.status_text = (
                f"{attacker.unit_id} dealt {resolution.predicted_damage} and defeated {defender.unit_id}"
            )
        else:
            self._replace_unit(replace(defender, hp=resolution.defender_next_hp))
            self.combat_effects.append({
                "type": "hit_shake",
                "target_pos": defender.position,
                "frames_remaining": 8,
            })
            self.status_text = (
                f"{attacker.unit_id} dealt {resolution.predicted_damage} to {defender.unit_id}"
            )

    def _auto_switch_turn_if_needed(self) -> None:
        if self.game_over:
            return
        if has_unacted_units(self.units, unit_system.Side.PLAYER, self.acted_unit_ids):
            return
        self._switch_to_enemy_turn(manual=False)

    def _switch_to_enemy_turn(self, manual: bool) -> None:
        if self.game_over:
            return
        self._clear_selection()
        self.current_turn = unit_system.Side.ENEMY
        self.enemy_turn_countdown = ENEMY_TURN_DELAY_FRAMES
        self.enemy_acted_unit_ids.clear()
        if manual:
            self.status_text = "Player ended turn manually"
        else:
            self.status_text = "All units acted; enemy turn"

    def _check_battle_end(self) -> bool:
        if self.game_over:
            return True

        player_lord_alive = self._unit_by_id(PLAYER_COMMANDER_ID) is not None
        enemy_lord_alive = self._unit_by_id(ENEMY_COMMANDER_ID) is not None
        if player_lord_alive and enemy_lord_alive:
            return False

        self.game_over = True
        self.enemy_turn_countdown = 0
        self._clear_selection()

        if enemy_lord_alive:
            self.winner_side = unit_system.Side.ENEMY
            self.status_text = "Defeat: your commander was defeated"
        else:
            self.winner_side = unit_system.Side.PLAYER
            self.status_text = "Victory: enemy commander defeated"
        return True

    def _unit_by_id(self, unit_id: str | None) -> "unit_system.Unit | None":
        if unit_id is None:
            return None
        for unit in self.units:
            if unit.unit_id == unit_id:
                return unit
        return None

    def _unit_at(self, tile: tuple[int, int]) -> "unit_system.Unit | None":
        for unit in self.units:
            if unit.position == tile:
                return unit
        return None

    def _replace_unit(self, next_unit: "unit_system.Unit") -> None:
        self.units = [next_unit if unit.unit_id == next_unit.unit_id else unit for unit in self.units]

    def _remove_unit(self, unit_id: str) -> None:
        self.units = [unit for unit in self.units if unit.unit_id != unit_id]
        self.acted_unit_ids.discard(unit_id)
        self.enemy_acted_unit_ids.discard(unit_id)
        if self.selected_unit_id == unit_id:
            self._clear_selection()

    def _clear_selection(self) -> None:
        self.selected_unit_id = None
        self.move_candidates.clear()
        self.attack_candidates.clear()

    def _screen_to_map_tile(self, screen_x: int, screen_y: int) -> tuple[int, int] | None:
        if screen_y < TOP_BAR_HEIGHT or screen_y >= SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT:
            return None
        map_x = int((screen_x + self.camera_x) // TILE_SIZE)
        map_y = int((screen_y + self.camera_y) // TILE_SIZE)
        if 0 <= map_x < self.map_width and 0 <= map_y < self.map_height:
            return map_x, map_y
        return None

    def _map_to_screen_pixel(self, map_x: int, map_y: int) -> tuple[int, int]:
        return map_x * TILE_SIZE - int(self.camera_x), map_y * TILE_SIZE - int(self.camera_y)

    def _update_hovered_unit(self) -> None:
        hovered_tile = self._screen_to_map_tile(pyxel.mouse_x, pyxel.mouse_y)
        if hovered_tile is None:
            self.hovered_unit_id = None
            return

        hovered_unit = self._unit_at(hovered_tile)
        self.hovered_unit_id = hovered_unit.unit_id if hovered_unit else None

    def _is_mouse_on_end_turn_button(self, x: int, y: int) -> bool:
        bx, by, bw, bh = END_TURN_BUTTON
        return bx <= x < bx + bw and by <= y < by + bh

    def _update_edge_scroll(self) -> None:
        mouse_x = pyxel.mouse_x
        mouse_y = pyxel.mouse_y

        if 0 <= mouse_x < EDGE_SCROLL_MARGIN:
            ratio = (EDGE_SCROLL_MARGIN - mouse_x) / EDGE_SCROLL_MARGIN
            self.camera_x -= SCROLL_SPEED * ratio
        elif SCREEN_WIDTH - EDGE_SCROLL_MARGIN <= mouse_x < SCREEN_WIDTH:
            ratio = (mouse_x - (SCREEN_WIDTH - EDGE_SCROLL_MARGIN)) / EDGE_SCROLL_MARGIN
            self.camera_x += SCROLL_SPEED * ratio

        if 0 <= mouse_y < EDGE_SCROLL_MARGIN:
            ratio = (EDGE_SCROLL_MARGIN - mouse_y) / EDGE_SCROLL_MARGIN
            self.camera_y -= SCROLL_SPEED * ratio
        elif SCREEN_HEIGHT - EDGE_SCROLL_MARGIN <= mouse_y < SCREEN_HEIGHT:
            ratio = (mouse_y - (SCREEN_HEIGHT - EDGE_SCROLL_MARGIN)) / EDGE_SCROLL_MARGIN
            self.camera_y += SCROLL_SPEED * ratio

        self.camera_x = min(max(self.camera_x, 0.0), self.max_camera_x)
        self.camera_y = min(max(self.camera_y, 0.0), self.max_camera_y)

    def draw(self) -> None:
        if self.game_state == GameState.TITLE:
            self._draw_title_screen()
            return

        pyxel.cls(0)

        start_tile_x = int(self.camera_x // TILE_SIZE)
        start_tile_y = int(self.camera_y // TILE_SIZE)
        offset_x = -int(self.camera_x % TILE_SIZE)
        offset_y = -int(self.camera_y % TILE_SIZE)

        for screen_ty in range(VISIBLE_TILES_Y + 2):
            map_y = start_tile_y + screen_ty
            if map_y >= self.map_height:
                continue

            draw_y = offset_y + screen_ty * TILE_SIZE
            for screen_tx in range(VISIBLE_TILES_X + 2):
                map_x = start_tile_x + screen_tx
                if map_x >= self.map_width:
                    continue

                draw_x = offset_x + screen_tx * TILE_SIZE
                terrain = self.terrain_map[map_y][map_x]
                self._draw_terrain_tile(draw_x, draw_y, terrain)

        self._draw_action_candidates()
        self._draw_units()
        self._draw_combat_effects()
        self._draw_floating_text()
        self._draw_top_bar()
        self._draw_bottom_bar()
        self._draw_hover_unit_info()
        self._draw_battle_result()

    def _draw_action_candidates(self) -> None:
        for map_x, map_y in self.move_candidates:
            sx, sy = self._map_to_screen_pixel(map_x, map_y)
            if sx <= -TILE_SIZE or sy <= -TILE_SIZE or sx >= SCREEN_WIDTH or sy >= SCREEN_HEIGHT:
                continue
            pyxel.rect(sx + 2, sy + 2, TILE_SIZE - 4, TILE_SIZE - 4, 11)
            pyxel.rectb(sx + 1, sy + 1, TILE_SIZE - 2, TILE_SIZE - 2, 11)

        for map_x, map_y in self.attack_candidates:
            sx, sy = self._map_to_screen_pixel(map_x, map_y)
            if sx <= -TILE_SIZE or sy <= -TILE_SIZE or sx >= SCREEN_WIDTH or sy >= SCREEN_HEIGHT:
                continue
            pyxel.rectb(sx + 1, sy + 1, TILE_SIZE - 2, TILE_SIZE - 2, 9)
            pyxel.rectb(sx + 2, sy + 2, TILE_SIZE - 4, TILE_SIZE - 4, 9)

    def _draw_units(self) -> None:
        for unit in self.units:
            sx, sy = self._map_to_screen_pixel(unit.position[0], unit.position[1])
            if sx <= -TILE_SIZE or sy <= -TILE_SIZE or sx >= SCREEN_WIDTH or sy >= SCREEN_HEIGHT:
                continue

            is_player = unit.side == unit_system.Side.PLAYER
            is_acted = unit.unit_id in self.acted_unit_ids or unit.unit_id in self.enemy_acted_unit_ids

            if is_acted:
                base_color = 5
            else:
                base_color = 3 if is_player else 2

            pyxel.rect(sx + 2, sy + 2, TILE_SIZE - 4, TILE_SIZE - 4, base_color)
            pyxel.rectb(sx + 2, sy + 2, TILE_SIZE - 4, TILE_SIZE - 4, 0)

            unit_type = unit.unit_type
            if unit_type == unit_system.UnitType.SPEAR:
                pyxel.line(sx + 8, sy + 3, sx + 4, sy + 10, 7)
                pyxel.line(sx + 8, sy + 3, sx + 12, sy + 10, 7)
                pyxel.line(sx + 4, sy + 10, sx + 12, sy + 10, 7)
            elif unit_type == unit_system.UnitType.CAVALRY:
                pyxel.rect(sx + 4, sy + 4, 8, 6, 7)
                pyxel.rect(sx + 5, sy + 3, 2, 2, 7)
                pyxel.rect(sx + 9, sy + 3, 2, 2, 7)
            elif unit_type == unit_system.UnitType.ARCHER:
                pyxel.line(sx + 8, sy + 3, sx + 5, sy + 11, 7)
                pyxel.line(sx + 8, sy + 3, sx + 11, sy + 11, 7)
                pyxel.pset(sx + 8, sy + 3, 7)

            hp_bar_width = 10
            hp_bar_height = 2
            hp_ratio = max(0, unit.hp / 100)
            hp_color = 11 if hp_ratio > 0.5 else (10 if hp_ratio > 0.25 else 8)
            pyxel.rect(sx + 3, sy + 13, hp_bar_width, hp_bar_height, 0)
            pyxel.rect(sx + 3, sy + 13, int(hp_bar_width * hp_ratio), hp_bar_height, hp_color)

            if not is_acted and is_player:
                pyxel.pset(sx + 13, sy + 2, 11)

            if unit.unit_id == self.selected_unit_id:
                pulse = 7 if (pyxel.frame_count // 6) % 2 == 0 else 0
                pyxel.rectb(sx - 1, sy - 1, TILE_SIZE + 2, TILE_SIZE + 2, pulse)

    def _draw_top_bar(self) -> None:
        pyxel.rect(0, 0, SCREEN_WIDTH, TOP_BAR_HEIGHT, 0)
        pyxel.rect(0, TOP_BAR_HEIGHT - 2, SCREEN_WIDTH, 2, 5)

        accent_color = 5
        for i in range(0, SCREEN_WIDTH, 8):
            pyxel.rect(i, TOP_BAR_HEIGHT - 2, 2, 2, accent_color if i % 16 == 0 else 3)

        if self.game_over:
            turn_text = "BATTLE END"
            turn_color = 7
        else:
            turn_text = "PLAYER" if self.current_turn == unit_system.Side.PLAYER else "ENEMY"
            turn_color = 3 if self.current_turn == unit_system.Side.PLAYER else 2

        self._draw_text(4, 4, "TURN:", 6, compact=True)
        self._draw_text_shadowed(32, 4, turn_text, turn_color, shadow_color=0, compact=True)

        if self.current_turn == unit_system.Side.PLAYER and not self.game_over:
            pyxel.rect(4, 13, 26, 3, 3)

        button_x, button_y, button_w, button_h = END_TURN_BUTTON
        button_hovered = self._is_mouse_on_end_turn_button(pyxel.mouse_x, pyxel.mouse_y)
        if self.current_turn == unit_system.Side.PLAYER and not self.game_over:
            button_color = 10 if button_hovered else 2
            text_color = 0 if button_hovered else 7
        else:
            button_color = 5
            text_color = 6
        pyxel.rect(button_x, button_y, button_w, button_h, button_color)
        pyxel.rectb(button_x, button_y, button_w, button_h, 7)
        self._draw_text_shadowed(button_x + 8, button_y + 3, "End Turn", text_color, shadow_color=0, compact=True)

    def _draw_bottom_bar(self) -> None:
        pyxel.rect(0, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT, SCREEN_WIDTH, BOTTOM_BAR_HEIGHT, 0)
        pyxel.rect(0, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT, SCREEN_WIDTH, 2, 5)

        for i in range(0, SCREEN_WIDTH, 8):
            pyxel.rect(i, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT + 12, 2, 2, 3 if i % 16 == 0 else 1)

        status_y = SCREEN_HEIGHT - 10
        self._draw_text(4, status_y, self.status_text[:52], 7, compact=True)

    def _draw_hover_unit_info(self) -> None:
        unit = self._unit_by_id(self.hovered_unit_id)
        if unit is None:
            return

        stats = unit_system.get_unit_stats(unit.unit_type)
        is_player = unit.side == unit_system.Side.PLAYER
        side_label = "PLAYER" if is_player else "ENEMY"
        unit_type_label = unit.unit_type.value.upper()

        box_w = 120
        box_h = 54
        box_x = min(max(pyxel.mouse_x + 12, 2), SCREEN_WIDTH - box_w - 2)
        box_y = min(max(pyxel.mouse_y + 12, TOP_BAR_HEIGHT + 2), SCREEN_HEIGHT - box_h - BOTTOM_BAR_HEIGHT)

        pyxel.rect(box_x, box_y, box_w, box_h, 0)
        pyxel.rectb(box_x, box_y, box_w, box_h, 7)

        header_color = 3 if is_player else 2
        self._draw_text_shadowed(box_x + 4, box_y + 3, f"[{side_label}]", header_color, shadow_color=0, compact=True)

        self._draw_text(box_x + 4, box_y + 14, f"TYPE:{unit_type_label}", 6, compact=True)
        self._draw_text(box_x + 72, box_y + 14, f"HP:{unit.hp}", 10 if unit.hp > 30 else 8, compact=True)

        self._draw_text(box_x + 4, box_y + 24, f"ATK:{stats.attack}", 8, compact=True)
        self._draw_text(box_x + 48, box_y + 24, f"DEF:{stats.defense}", 6, compact=True)
        self._draw_text(box_x + 88, box_y + 24, f"MOV:{stats.movement}", 11, compact=True)

        range_text = f"RNG:{stats.min_range}-{stats.max_range}"
        self._draw_text(box_x + 4, box_y + 34, range_text, 12 if stats.max_range > 1 else 6, compact=True)

        if unit.unit_id in self.acted_unit_ids or unit.unit_id in self.enemy_acted_unit_ids:
            self._draw_text(box_x + 70, box_y + 34, "[ACTED]", 5, compact=True)

    def _draw_terrain_tile(self, x: int, y: int, terrain: Terrain) -> None:
        pyxel.rect(x, y, TILE_SIZE, TILE_SIZE, TERRAIN_COLOR[terrain])

        if terrain == Terrain.PLAIN:
            pyxel.pset(x + 2, y + 4, 11)
            pyxel.pset(x + 8, y + 10, 11)
            pyxel.pset(x + 13, y + 6, 11)
            pyxel.pset(x + 5, y + 12, 11)
            pyxel.pset(x + 11, y + 2, 11)
        elif terrain == Terrain.FOREST:
            pyxel.rect(x + 6, y + 2, 4, 8, 3)
            pyxel.rect(x + 5, y + 3, 6, 6, 11)
            pyxel.pset(x + 7, y + 4, 3)
            pyxel.pset(x + 10, y + 5, 3)
            pyxel.rect(x + 2, y + 10, 3, 3, 3)
            pyxel.rect(x + 11, y + 9, 3, 4, 3)
        elif terrain == Terrain.RIVER:
            pyxel.rect(x + 1, y + 3, 14, 2, 12)
            pyxel.rect(x + 2, y + 8, 12, 2, 12)
            pyxel.rect(x, y + 12, 16, 2, 12)
            pyxel.pset(x + 3, y + 4, 7)
            pyxel.pset(x + 8, y + 9, 7)
            pyxel.pset(x + 5, y + 13, 7)
        elif terrain == Terrain.SEA:
            pyxel.rect(x, y + 2, 16, 3, 12)
            pyxel.rect(x + 2, y + 7, 12, 2, 12)
            pyxel.rect(x, y + 11, 16, 3, 12)
            pyxel.pset(x + 2, y + 3, 6)
            pyxel.pset(x + 10, y + 5, 6)
            pyxel.pset(x + 6, y + 12, 6)

    def _draw_title_screen(self) -> None:
        pyxel.cls(1)

        for i in range(8):
            for j in range(12):
                x = i * 20 + (j % 2) * 10
                y = j * 16
                shade = 3 if (i + j) % 2 == 0 else 5
                pyxel.rect(x, y, 20, 16, shade)

        title_box_x = SCREEN_WIDTH // 2 - 70
        title_box_y = 40
        title_box_w = 140
        title_box_h = 90
        pyxel.rect(title_box_x, title_box_y, title_box_w, title_box_h, 0)
        pyxel.rectb(title_box_x, title_box_y, title_box_w, title_box_h, 7)

        self._draw_text_shadowed(title_box_x + 33, title_box_y + 18, "PIXEL", 12, shadow_color=0, compact=True)
        self._draw_text_shadowed(title_box_x + 50, title_box_y + 34, "SRPG", 11, shadow_color=0, compact=True)

        pyxel.rect(title_box_x + 20, title_box_y + 52, 100, 2, 5)

        blink = (self.title_frame // 30) % 2 == 0
        if blink:
            self._draw_text_shadowed(title_box_x + 20, title_box_y + 70, "Click to Start", 7, shadow_color=0, compact=True)

        self._draw_text(SCREEN_WIDTH // 2 - 40, SCREEN_HEIGHT - 20, "WASD/Arrows to Move", 6, compact=True)
        self._draw_text(SCREEN_WIDTH // 2 - 36, SCREEN_HEIGHT - 12, "Edge Scroll: Mouse", 6, compact=True)

    def _draw_combat_effects(self) -> None:
        for effect in self.combat_effects:
            effect_type = effect.get("type", "")
            pos = effect.get("target_pos", (0, 0))
            frames = effect.get("frames_remaining", 0)
            sx, sy = self._map_to_screen_pixel(pos[0], pos[1])
            if sx <= -TILE_SIZE or sy <= -TILE_SIZE or sx >= SCREEN_WIDTH or sy >= SCREEN_HEIGHT:
                continue

            if effect_type == "attack_flash":
                alpha = min(1.0, frames / 5)
                if alpha > 0.5:
                    pyxel.rect(sx + 1, sy + 1, TILE_SIZE - 2, TILE_SIZE - 2, 7)

            elif effect_type == "hit_shake":
                shake = (5 - frames) % 3 - 1
                pyxel.rect(sx + 2 + shake, sy + 2, TILE_SIZE - 4, TILE_SIZE - 4, 8)
                pyxel.rectb(sx + 2 + shake, sy + 2, TILE_SIZE - 4, TILE_SIZE - 4, 9)

            elif effect_type == "defeat_burst":
                progress = 1.0 - (frames / 20)
                radius = int(progress * 20)
                for angle in range(0, 360, 45):
                    rad = angle * 3.14159 / 180
                    px = sx + 8 + int(radius * 0.7 * (rad - 0.5))
                    py = sy + 8 + int(radius * 0.7 * (rad - 0.5))
                    if 0 <= px < SCREEN_WIDTH and 0 <= py < SCREEN_HEIGHT:
                        pyxel.pset(px, py, 2)

    def _draw_floating_text(self) -> None:
        for ft in self.floating_texts:
            x = ft["x"] - int(self.camera_x)
            y = ft["y"] - int(self.camera_y)
            if 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT:
                alpha = ft["frames_remaining"] / 30
                color = ft["color"]
                self._draw_text_shadowed(x - 8, y, ft["text"], color, shadow_color=0, compact=True)

    def _draw_battle_result(self) -> None:
        if not self.game_over:
            return

        box_w = 160
        box_h = 60
        box_x = (SCREEN_WIDTH - box_w) // 2
        box_y = (SCREEN_HEIGHT - box_h) // 2

        pyxel.rect(box_x - 4, box_y - 4, box_w + 8, box_h + 8, 0)
        pyxel.rect(box_x, box_y, box_w, box_h, 0)
        pyxel.rectb(box_x, box_y, box_w, box_h, 7)

        for i in range(0, box_w, 8):
            pyxel.rect(box_x + i, box_y + box_h - 4, 4, 2, 5 if i % 16 == 0 else 3)

        result_text = "VICTORY" if self.winner_side == unit_system.Side.PLAYER else "DEFEAT"
        result_color = 3 if self.winner_side == unit_system.Side.PLAYER else 2
        self._draw_text_shadowed(box_x + 58, box_y + 12, result_text, result_color, shadow_color=0, compact=True)

        sub_text = "Enemy commander defeated!" if self.winner_side == unit_system.Side.PLAYER else "Your commander fell..."
        self._draw_text(box_x + 16, box_y + 30, sub_text, 6, compact=True)

        blink = (pyxel.frame_count // 20) % 2 == 0
        if blink:
            self._draw_text_shadowed(box_x + 40, box_y + 46, "- Click to Restart -", 5, shadow_color=0, compact=True)


if __name__ == "__main__":
    Game()
