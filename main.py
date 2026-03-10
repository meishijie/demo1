from __future__ import annotations

import random
from enum import IntEnum

import pyxel

try:
    import unit_system  # Optional integration hook for later waves.
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
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Pyxel SRPG Prototype", fps=30)
        pyxel.mouse(True)

        self.map_width = MAP_WIDTH
        self.map_height = MAP_HEIGHT
        self.terrain_map = _generate_map(self.map_width, self.map_height)

        self.camera_x = 0.0
        self.camera_y = 0.0

        self.max_camera_x = max(0, self.map_width * TILE_SIZE - SCREEN_WIDTH)
        self.max_camera_y = max(0, self.map_height * TILE_SIZE - SCREEN_HEIGHT)

        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        self._update_edge_scroll()

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

        self._draw_debug_overlay()

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

    def _draw_debug_overlay(self) -> None:
        cam_tile_x = int(self.camera_x // TILE_SIZE)
        cam_tile_y = int(self.camera_y // TILE_SIZE)

        pyxel.rect(0, 0, 320, 16, 0)
        pyxel.text(4, 4, f"cam:({cam_tile_x},{cam_tile_y}) map:40x40 tile:16", 7)

        pyxel.rect(0, SCREEN_HEIGHT - 8, 320, 8, 0)
        pyxel.text(
            4,
            SCREEN_HEIGHT - 6,
            "terrain: plain green / forest dark / river+sea blocked (mouse edge scroll)",
            7,
        )


if __name__ == "__main__":
    Game()
