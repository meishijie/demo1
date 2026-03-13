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
    MAGE = "mage"
    HEALER = "healer"
    SLIME = "slime"


class TerrainType(str, Enum):
    PLAIN = "plain"
    FOREST = "forest"
    RIVER = "river"
    SEA = "sea"
    FIRE = "fire"


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
    knockback_dist: int = 0

BASE_UNIT_STATS: dict[UnitType, UnitStats] = {
    UnitType.SPEAR: UnitStats(attack=24, defense=14, movement=3, min_range=1, max_range=1),
    UnitType.CAVALRY: UnitStats(attack=28, defense=12, movement=5, min_range=1, max_range=1),
    UnitType.ARCHER: UnitStats(attack=20, defense=10, movement=3, min_range=2, max_range=3),
    UnitType.MAGE: UnitStats(attack=30, defense=5, movement=2, min_range=1, max_range=2),
    UnitType.HEALER: UnitStats(attack=5, defense=5, movement=3, min_range=1, max_range=2),
    UnitType.SLIME: UnitStats(attack=18, defense=8, movement=2, min_range=1, max_range=1),
} # attack is used for healing power

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


def _normalize_terrain(terrain: TerrainType | str) -> TerrainType:
    if isinstance(terrain, TerrainType):
        return terrain
    return TerrainType(str(terrain).lower())


def get_unit_stats(unit_type: UnitType) -> UnitStats:
    return BASE_UNIT_STATS[unit_type]


def counter_multiplier(attacker_type: UnitType, defender_type: UnitType) -> float:
    if (attacker_type, defender_type) in COUNTER_RELATIONSHIPS:
        return COUNTER_ADVANTAGE_MULTIPLIER
    if (defender_type, attacker_type) in COUNTER_RELATIONSHIPS:
        return COUNTER_DISADVANTAGE_MULTIPLIER
    return 1.0


def terrain_defense_bonus(terrain: TerrainType | str) -> int:
    terrain_type = _normalize_terrain(terrain)
    if terrain_type is TerrainType.FOREST:
        return FOREST_DEFENSE_BONUS
    return 0


def movement_cost(unit_type: UnitType, terrain: TerrainType | str) -> int:
    terrain_type = _normalize_terrain(terrain)
    cost = 1
    if unit_type is UnitType.CAVALRY and terrain_type is TerrainType.FOREST:
        cost += CAVALRY_FOREST_MOVE_PENALTY
    return cost


def can_unit_enter_tile(
    terrain: TerrainType | str,
    unit_type: UnitType | str | None = None,
) -> bool:
    # unit_type is reserved for future per-unit passability rules.
    _ = unit_type

    terrain_type = _normalize_terrain(terrain)
    return terrain_type not in IMPASSABLE_TERRAINS


def get_aura_bonus(unit: Unit, units: Sequence[Unit]) -> int:
    """Check if the unit is near a friendly Lord commander and gets attack bonus."""
    bonus = 0
    for other in units:
        if other.side == unit.side and "lord" in other.unit_id and other.unit_id != unit.unit_id:
            distance = abs(unit.position[0] - other.position[0]) + abs(unit.position[1] - other.position[1])
            if distance <= 2:
                bonus = 6  # +6 Attack from Aura
                break
    return bonus

def preview_combat(attacker: Unit, defender: Unit, defender_terrain: TerrainType, all_units: Sequence[Unit] = ()) -> CombatPreview:
    if attacker.unit_type == UnitType.HEALER:
        # For healer, predict heal amount!
        heal_power = get_unit_stats(attacker.unit_type).attack
        return CombatPreview(attacker_multiplier=1.0, defender_defense_bonus=0, predicted_damage=-heal_power)

    attacker_stats = get_unit_stats(attacker.unit_type)
    defender_stats = get_unit_stats(defender.unit_type)
    multiplier = counter_multiplier(attacker.unit_type, defender.unit_type)
    
    # Mage ignores terrain defense
    defense_bonus = 0 if attacker.unit_type == UnitType.MAGE else terrain_defense_bonus(defender_terrain)
    
    # Commander Aura Bonus
    aura_bonus = get_aura_bonus(attacker, all_units)

    raw_damage = (attacker_stats.attack + aura_bonus) * multiplier - (defender_stats.defense + defense_bonus)
    # Give Mage intrinsic magic advantage: less variance with physical defense
    if attacker.unit_type == UnitType.MAGE:
        # Ignore half of physical defense roughly by adding pen
        raw_damage += defender_stats.defense // 2

    predicted_damage = max(1, int(round(raw_damage)))
    
    distance = abs(attacker.position[0] - defender.position[0]) + abs(attacker.position[1] - defender.position[1])
    knockback = 0
    if distance == 1:
        if attacker.unit_type == UnitType.CAVALRY:
            knockback = 2
        elif attacker.unit_type == UnitType.SPEAR:
            knockback = 1

    return CombatPreview(
        attacker_multiplier=multiplier,
        defender_defense_bonus=defense_bonus,
        predicted_damage=predicted_damage,
        knockback_dist=knockback,
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
    terrain_map: Mapping[Coord, TerrainType | str],
    map_width: int,
    map_height: int,
) -> set[Coord]:
    stats = get_unit_stats(unit.unit_type)
    occupied = {other.position for other in units if other.side != unit.side and other.unit_id != unit.unit_id}
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

            terrain = _normalize_terrain(terrain_map.get(nxt, TerrainType.PLAIN))
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
    terrain_map: Mapping[Coord, TerrainType | str],
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
