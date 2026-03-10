from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

Coord = tuple[int, int]


class Side(str, Enum):
    PLAYER = "player"
    ENEMY = "enemy"


class UnitType(str, Enum):
    SPEAR = "spear"
    CAVALRY = "cavalry"
    ARCHER = "archer"


class TerrainType(str, Enum):
    PLAIN = "plain"
    FOREST = "forest"
    RIVER = "river"
    SEA = "sea"


@dataclass(frozen=True)
class UnitStats:
    attack: int
    defense: int
    movement: int
    min_range: int
    max_range: int


@dataclass(frozen=True)
class Unit:
    unit_id: str
    side: Side
    unit_type: UnitType
    position: Coord
    hp: int = 100


@dataclass(frozen=True)
class CombatPreview:
    attacker_multiplier: float
    defender_defense_bonus: int
    predicted_damage: int


BASE_UNIT_STATS: dict[UnitType, UnitStats] = {
    UnitType.SPEAR: UnitStats(attack=24, defense=14, movement=3, min_range=1, max_range=1),
    UnitType.CAVALRY: UnitStats(attack=28, defense=12, movement=5, min_range=1, max_range=1),
    UnitType.ARCHER: UnitStats(attack=20, defense=10, movement=3, min_range=2, max_range=3),
}

# 枪克骑、骑克弓、弓克枪
COUNTER_RELATIONSHIPS: set[tuple[UnitType, UnitType]] = {
    (UnitType.SPEAR, UnitType.CAVALRY),
    (UnitType.CAVALRY, UnitType.ARCHER),
    (UnitType.ARCHER, UnitType.SPEAR),
}

COUNTER_ADVANTAGE_MULTIPLIER = 1.25
COUNTER_DISADVANTAGE_MULTIPLIER = 0.75

FOREST_DEFENSE_BONUS = 2
CAVALRY_FOREST_MOVE_PENALTY = 1
IMPASSABLE_TERRAINS: set[TerrainType] = {TerrainType.RIVER, TerrainType.SEA}


def get_unit_stats(unit_type: UnitType) -> UnitStats:
    return BASE_UNIT_STATS[unit_type]


def counter_multiplier(attacker_type: UnitType, defender_type: UnitType) -> float:
    if (attacker_type, defender_type) in COUNTER_RELATIONSHIPS:
        return COUNTER_ADVANTAGE_MULTIPLIER
    if (defender_type, attacker_type) in COUNTER_RELATIONSHIPS:
        return COUNTER_DISADVANTAGE_MULTIPLIER
    return 1.0


def terrain_defense_bonus(terrain: TerrainType) -> int:
    if terrain is TerrainType.FOREST:
        return FOREST_DEFENSE_BONUS
    return 0


def movement_cost(unit_type: UnitType, terrain: TerrainType) -> int:
    cost = 1
    if unit_type is UnitType.CAVALRY and terrain is TerrainType.FOREST:
        cost += CAVALRY_FOREST_MOVE_PENALTY
    return cost


def can_unit_enter_tile(
    terrain: TerrainType | str,
    unit_type: UnitType | str | None = None,
) -> bool:
    # unit_type is reserved for future per-unit passability rules.
    _ = unit_type

    if isinstance(terrain, TerrainType):
        terrain_type = terrain
    else:
        try:
            terrain_type = TerrainType(str(terrain).lower())
        except ValueError:
            return True

    return terrain_type not in IMPASSABLE_TERRAINS


def preview_combat(attacker: Unit, defender: Unit, defender_terrain: TerrainType) -> CombatPreview:
    attacker_stats = get_unit_stats(attacker.unit_type)
    defender_stats = get_unit_stats(defender.unit_type)
    multiplier = counter_multiplier(attacker.unit_type, defender.unit_type)
    defense_bonus = terrain_defense_bonus(defender_terrain)
    raw_damage = attacker_stats.attack * multiplier - (defender_stats.defense + defense_bonus)
    predicted_damage = max(1, int(round(raw_damage)))
    return CombatPreview(
        attacker_multiplier=multiplier,
        defender_defense_bonus=defense_bonus,
        predicted_damage=predicted_damage,
    )


def _in_bounds(pos: Coord, map_width: int, map_height: int) -> bool:
    x, y = pos
    return 0 <= x < map_width and 0 <= y < map_height


def _neighbors(pos: Coord) -> tuple[Coord, Coord, Coord, Coord]:
    x, y = pos
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def build_enemy_zoc(
    units: Sequence[Unit],
    side: Side,
    map_width: int,
    map_height: int,
) -> set[Coord]:
    enemy_side = Side.ENEMY if side is Side.PLAYER else Side.PLAYER
    zoc: set[Coord] = set()
    for unit in units:
        if unit.side is not enemy_side:
            continue
        for pos in _neighbors(unit.position):
            if _in_bounds(pos, map_width, map_height):
                zoc.add(pos)
    return zoc


def reachable_tiles(
    unit: Unit,
    units: Sequence[Unit],
    terrain_map: Mapping[Coord, TerrainType],
    map_width: int,
    map_height: int,
) -> set[Coord]:
    stats = get_unit_stats(unit.unit_type)
    occupied = {other.position for other in units if other.unit_id != unit.unit_id}
    enemy_zoc = build_enemy_zoc(units, side=unit.side, map_width=map_width, map_height=map_height)

    best_remaining_mp: dict[Coord, int] = {unit.position: stats.movement}
    queue: deque[tuple[Coord, int]] = deque([(unit.position, stats.movement)])

    while queue:
        current, remaining_mp = queue.popleft()
        for nxt in _neighbors(current):
            if not _in_bounds(nxt, map_width, map_height):
                continue
            if nxt in occupied:
                continue

            terrain = terrain_map.get(nxt, TerrainType.PLAIN)
            if not can_unit_enter_tile(terrain=terrain, unit_type=unit.unit_type):
                continue

            step_cost = movement_cost(unit.unit_type, terrain)
            new_remaining = remaining_mp - step_cost
            if new_remaining < 0:
                continue

            # ZOC 限制：不允许从敌方 ZOC 格直接移动到另一个敌方 ZOC 格。
            if current in enemy_zoc and nxt in enemy_zoc:
                continue

            # 进入敌方 ZOC 后立即停下，不能继续扩展路径。
            if nxt in enemy_zoc:
                new_remaining = 0

            prev_best = best_remaining_mp.get(nxt, -1)
            if new_remaining <= prev_best:
                continue

            best_remaining_mp[nxt] = new_remaining
            if new_remaining > 0:
                queue.append((nxt, new_remaining))

    best_remaining_mp.pop(unit.position, None)
    return set(best_remaining_mp)


def can_move_to(
    unit: Unit,
    target: Coord,
    units: Sequence[Unit],
    terrain_map: Mapping[Coord, TerrainType],
    map_width: int,
    map_height: int,
) -> bool:
    return target in reachable_tiles(
        unit=unit,
        units=units,
        terrain_map=terrain_map,
        map_width=map_width,
        map_height=map_height,
    )
