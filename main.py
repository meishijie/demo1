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

TOP_BAR_HEIGHT = 16
BOTTOM_BAR_HEIGHT = 12
END_TURN_BUTTON = (SCREEN_WIDTH - 72, 2, 68, 12)
PLAYER_COMMANDER_ID = "p_lord"
ENEMY_COMMANDER_ID = "e_lord"


class Terrain(IntEnum):
    PLAIN = 0
    FOREST = 1
    RIVER = 2
    SEA = 3


TERRAIN_COLOR = {
    Terrain.PLAIN: 3,
    Terrain.FOREST: 11,
    Terrain.RIVER: 12,
    Terrain.SEA: 1,
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

        self.default_font, self.compact_font = self._load_fonts()

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
        self._update_edge_scroll()
        self._update_hovered_unit()
        if self.game_over or self._check_battle_end():
            return

        if self.current_turn == unit_system.Side.ENEMY:
            self._update_enemy_turn()
            return

        self._handle_player_input()

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
        if resolution.defender_defeated:
            self._remove_unit(defender.unit_id)
            self.status_text = (
                f"{attacker.unit_id} dealt {resolution.predicted_damage} and defeated {defender.unit_id}"
            )
        else:
            self._replace_unit(replace(defender, hp=resolution.defender_next_hp))
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
        self._draw_top_bar()
        self._draw_bottom_bar()
        self._draw_hover_unit_info()
        self._draw_battle_result()

    def _draw_action_candidates(self) -> None:
        for map_x, map_y in self.move_candidates:
            sx, sy = self._map_to_screen_pixel(map_x, map_y)
            if sx <= -TILE_SIZE or sy <= -TILE_SIZE or sx >= SCREEN_WIDTH or sy >= SCREEN_HEIGHT:
                continue
            pyxel.rectb(sx + 1, sy + 1, TILE_SIZE - 2, TILE_SIZE - 2, 10)

        for map_x, map_y in self.attack_candidates:
            sx, sy = self._map_to_screen_pixel(map_x, map_y)
            if sx <= -TILE_SIZE or sy <= -TILE_SIZE or sx >= SCREEN_WIDTH or sy >= SCREEN_HEIGHT:
                continue
            pyxel.rectb(sx + 2, sy + 2, TILE_SIZE - 4, TILE_SIZE - 4, 8)

    def _draw_units(self) -> None:
        for unit in self.units:
            sx, sy = self._map_to_screen_pixel(unit.position[0], unit.position[1])
            if sx <= -TILE_SIZE or sy <= -TILE_SIZE or sx >= SCREEN_WIDTH or sy >= SCREEN_HEIGHT:
                continue

            color = 10 if unit.side == unit_system.Side.PLAYER else 8
            if unit.side == unit_system.Side.PLAYER and unit.unit_id in self.acted_unit_ids:
                color = 5

            pyxel.rect(sx + 2, sy + 2, TILE_SIZE - 4, TILE_SIZE - 4, color)
            pyxel.rectb(sx + 2, sy + 2, TILE_SIZE - 4, TILE_SIZE - 4, 0)

            unit_mark = unit.unit_type.value[0].upper()
            pyxel.text(sx + 6, sy + 5, unit_mark, 7)

            if unit.unit_id == self.selected_unit_id:
                pyxel.rectb(sx, sy, TILE_SIZE, TILE_SIZE, 7)

    def _draw_top_bar(self) -> None:
        pyxel.rect(0, 0, SCREEN_WIDTH, TOP_BAR_HEIGHT, 0)
        if self.game_over:
            turn_text = "BATTLE END"
        else:
            turn_text = "TURN: PLAYER" if self.current_turn == unit_system.Side.PLAYER else "TURN: ENEMY"
        self._draw_text(4, 4, turn_text, 7, compact=True)

        button_x, button_y, button_w, button_h = END_TURN_BUTTON
        button_color = 2 if (self.current_turn == unit_system.Side.PLAYER and not self.game_over) else 5
        pyxel.rect(button_x, button_y, button_w, button_h, button_color)
        pyxel.rectb(button_x, button_y, button_w, button_h, 7)
        self._draw_text(button_x + 8, button_y + 3, "End Turn", 7, compact=True)

    def _draw_bottom_bar(self) -> None:
        pyxel.rect(0, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT, SCREEN_WIDTH, BOTTOM_BAR_HEIGHT, 0)
        self._draw_text(4, SCREEN_HEIGHT - 9, self.status_text[:56], 7, compact=True)

    def _draw_hover_unit_info(self) -> None:
        unit = self._unit_by_id(self.hovered_unit_id)
        if unit is None:
            return

        stats = unit_system.get_unit_stats(unit.unit_type)
        side_label = "玩家" if unit.side == unit_system.Side.PLAYER else "敌军"
        lines = [
            f"阵营: {side_label}",
            f"兵种: {unit.unit_type.value}",
            f"HP: {unit.hp}",
            f"ATK/DEF: {stats.attack}/{stats.defense}",
            f"MOV/RNG: {stats.movement} {stats.min_range}-{stats.max_range}",
        ]

        box_w = 142
        box_h = 66
        box_x = min(max(pyxel.mouse_x + 8, 2), SCREEN_WIDTH - box_w - 2)
        box_y = min(max(pyxel.mouse_y + 8, TOP_BAR_HEIGHT + 1), SCREEN_HEIGHT - box_h - BOTTOM_BAR_HEIGHT)

        compact = box_y + box_h >= SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT - 2

        pyxel.rect(box_x, box_y, box_w, box_h, 1)
        pyxel.rectb(box_x, box_y, box_w, box_h, 7)
        for i, line in enumerate(lines):
            self._draw_text(box_x + 4, box_y + 4 + i * 11, line, 7, compact=compact)

    def _draw_terrain_tile(self, x: int, y: int, terrain: Terrain) -> None:
        pyxel.rect(x, y, TILE_SIZE, TILE_SIZE, TERRAIN_COLOR[terrain])

        if terrain == Terrain.FOREST:
            pyxel.pset(x + 4, y + 3, 3)
            pyxel.pset(x + 10, y + 6, 3)
            pyxel.pset(x + 7, y + 12, 3)
            pyxel.pset(x + 12, y + 10, 3)
        elif terrain == Terrain.RIVER:
            pyxel.line(x, y + 6, x + TILE_SIZE - 1, y + 6, 7)
            pyxel.line(x + 2, y + 10, x + TILE_SIZE - 3, y + 10, 7)
        elif terrain == Terrain.SEA:
            pyxel.line(x + 1, y + 5, x + TILE_SIZE - 2, y + 5, 6)
            pyxel.line(x + 3, y + 11, x + TILE_SIZE - 4, y + 11, 6)

    def _draw_battle_result(self) -> None:
        if not self.game_over:
            return

        box_w = 148
        box_h = 38
        box_x = (SCREEN_WIDTH - box_w) // 2
        box_y = (SCREEN_HEIGHT - box_h) // 2
        pyxel.rect(box_x, box_y, box_w, box_h, 0)
        pyxel.rectb(box_x, box_y, box_w, box_h, 7)

        result_text = "VICTORY" if self.winner_side == unit_system.Side.PLAYER else "DEFEAT"
        result_color = 11 if self.winner_side == unit_system.Side.PLAYER else 8
        self._draw_text(box_x + 48, box_y + 12, result_text, result_color, compact=True)


if __name__ == "__main__":
    Game()
