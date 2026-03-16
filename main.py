from __future__ import annotations

import os
import random
import copy
from dataclasses import dataclass, replace
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


@dataclass
class VFXEffect:
    x: float
    y: float
    type: str  # "text", "flash", "bump", "slash"
    text: str = ""
    color: int = 7
    life: int = 20
    max_life: int = 20
    vy: float = 0.0  # vertical velocity for floating text

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int

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
    BLOOD = 5


TERRAIN_COLOR = {
    Terrain.PLAIN: 3,
    Terrain.FOREST: 11,
    Terrain.RIVER: 12,
    Terrain.SEA: 1,
    Terrain.FIRE: 8,
    Terrain.BLOOD: 8,
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
        if attacker.unit_type == unit_system.UnitType.HEALER:
            if unit.side != attacker.side or unit.unit_id == attacker.unit_id or unit.hp >= 100:
                continue
        else:
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
        try:
            pyxel.load("assets/resource.pyxres")
        except Exception:
            pass
        
        self._init_sounds()
        try:
            pyxel.playm(0, loop=True)
        except Exception:
            pass
            
        pyxel.mouse(True)

        self.default_font, self.compact_font = self._load_fonts()
        self.state = GameState.TITLE
        self._init_game()
        
        pyxel.run(self.update, self.draw)

    def _init_sounds(self) -> None:
        # 0: Hit/Damage
        pyxel.sounds[0].set("a3a2c1a1", "n", "7", "s", 5)
        # 1: Move select
        pyxel.sounds[1].set("e2e3", "p", "7", "s", 4)
        # 2: Heal/Magic
        pyxel.sounds[2].set("c3e3g3c4", "s", "4444", "v", 5)

    def _init_game(self) -> None:
        self.map_width = MAP_WIDTH
        self.map_height = MAP_HEIGHT
        self.terrain_map = _generate_map(self.map_width, self.map_height)
        self.terrain_lookup = self._build_terrain_lookup()

        self.wave = 1
        self.score = 0

        self.camera_x = 0.0
        self.camera_y = 0.0

        self.max_camera_x = max(0, self.map_width * TILE_SIZE - SCREEN_WIDTH)
        self.max_camera_y = max(0, self.map_height * TILE_SIZE - SCREEN_HEIGHT)

        self.units = self._create_initial_units()
        self.current_turn = unit_system.Side.PLAYER
        self.acted_unit_ids = set()
        self.enemy_acted_unit_ids = set()

        self.selected_unit_id = None
        self.move_candidates = set()
        self.attack_candidates = set()

        self.hovered_unit_id = None
        self.enemy_turn_countdown = 0
        self.winner_side = None
        self.status_text = "Player turn: choose a unit [R:Rewind]"

        self.effects = []
        self.particles = []
        self.shake_x = 0
        self.shake_y = 0
        self.shake_duration = 0
        self.animating = False
        self.combat_queue = []
        self.move_queue = []
        self.hit_stop_frames = 0
        self.glitch_frames = 0
        self.history = []
        self.combat_timer = 0
        self.unit_offsets = {}

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
            unit_system.Unit("p_mage", unit_system.Side.PLAYER, unit_system.UnitType.MAGE, (5, 7), hp=100),
            unit_system.Unit("p_healer", unit_system.Side.PLAYER, unit_system.UnitType.HEALER, (6, 6), hp=100),
            unit_system.Unit("e_lord", unit_system.Side.ENEMY, unit_system.UnitType.SPEAR, (12, 7), hp=100),
            unit_system.Unit("e_cav", unit_system.Side.ENEMY, unit_system.UnitType.CAVALRY, (13, 9), hp=100),
            unit_system.Unit("e_arch", unit_system.Side.ENEMY, unit_system.UnitType.ARCHER, (15, 6), hp=100),
            unit_system.Unit("e_mage", unit_system.Side.ENEMY, unit_system.UnitType.MAGE, (14, 8), hp=100),
            unit_system.Unit("e_healer", unit_system.Side.ENEMY, unit_system.UnitType.HEALER, (15, 7), hp=100),
        ]

    def _build_terrain_lookup(self) -> dict[tuple[int, int], str]:
        lookup: dict[tuple[int, int], str] = {}
        for y, row in enumerate(self.terrain_map):
            for x, terrain in enumerate(row):
                lookup[(x, y)] = terrain.name.lower()
        return lookup

    def update(self) -> None:
        self._update_effects()
        self._look_update_shake()

        if self.hit_stop_frames > 0:
            self.hit_stop_frames -= 1
            return

        if self.glitch_frames > 0:
            self.glitch_frames -= 1

        if self.state == GameState.TITLE:
            self._update_title()
            return
        elif self.state == GameState.GAME_OVER:
            self._update_game_over()

        if self.state != GameState.TITLE:
            self._update_combat_animation()
            self._update_move_animation()

            if self.animating:
                return

            self._update_edge_scroll()
            self._update_hovered_unit()
            if self.state == GameState.GAME_OVER or self._check_battle_end():
                return

            if self.current_turn == unit_system.Side.ENEMY:
                self._update_enemy_turn()
                return

            self._handle_player_input()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
            self._init_game()
            self.state = GameState.PLAYING

    def _update_game_over(self) -> None:
        if self.enemy_turn_countdown > 0:
            self.enemy_turn_countdown -= 1
        else:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                self.state = GameState.TITLE

    def _add_effect(self, x: float, y: float, eff_type: str, text: str = "", color: int = 7, life: int = 20) -> None:
        vy = -1.5 if eff_type == "text" else 0.0
        self.effects.append(VFXEffect(x=x, y=y, type=eff_type, text=text, color=color, life=life, max_life=life, vy=vy))

    def _spawn_particles(self, cx: float, cy: float, count: int, colors: list[int]) -> None:
        for _ in range(count):
            angle = random.uniform(0, 6.28)
            speed = random.uniform(0.5, 2.0)
            vx = speed * pyxel.cos(angle * 180 / 3.14159)
            vy = -speed * pyxel.sin(angle * 180 / 3.14159) - 1.0 # Bias upwards
            life = random.randint(10, 25)
            color = random.choice(colors)
            self.particles.append(Particle(cx, cy, vx, vy, color, life))

    def _update_effects(self) -> None:
        for i in range(len(self.effects) - 1, -1, -1):
            eff = self.effects[i]
            eff.life -= 1
            if eff.type == "text":
                eff.y += eff.vy
                eff.vy += 0.15 # Gravity
            else:
                eff.y += eff.vy
            
            if eff.life <= 0:
                self.effects.pop(i)

        for i in range(len(self.particles) - 1, -1, -1):
            p = self.particles[i]
            p.life -= 1
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.2  # Gravity
            if p.life <= 0:
                self.particles.pop(i)

    def _trigger_shake(self, duration: int = 8) -> None:
        self.shake_duration = duration

    def _look_update_shake(self) -> None:
        if self.shake_duration > 0:
            self.shake_x = random.randint(-4, 4)
            self.shake_y = random.randint(-4, 4)
            self.shake_duration -= 1
        else:
            self.shake_x = 0
            self.shake_y = 0

    def _update_move_animation(self) -> None:
        if not self.move_queue:
            return

        self.combat_timer += 1
        curr = self.move_queue[0]
        unit_id = curr["unit_id"]
        start_tile = curr["start_tile"]
        target_tile = curr["target_tile"]

        # Duration 10 frames
        duration = 10
        if self.combat_timer <= duration:
            t = self.combat_timer / duration
            # Interpolate in pixels relative to center of start_tile
            dx = (target_tile[0] - start_tile[0]) * TILE_SIZE * t
            dy = (target_tile[1] - start_tile[1]) * TILE_SIZE * t
            self.unit_offsets[unit_id] = (dx, dy)
        else:
            # End of move
            self.unit_offsets[unit_id] = (0, 0)
            unit = self._unit_by_id(unit_id)
            if unit:
                target_terrain = self.terrain_map[target_tile[1]][target_tile[0]]
                occupant = self._unit_at(target_tile)
                
                if occupant and occupant.unit_id != unit_id:
                    # KATAMARI MERGE!
                    new_hp = min(500, unit.hp + occupant.hp)
                    # We must carefully remove occupant from units list without leaving blood
                    self.units = [u for u in self.units if u.unit_id != occupant.unit_id]
                    self.acted_unit_ids.discard(occupant.unit_id)
                    self.enemy_acted_unit_ids.discard(occupant.unit_id)
                    
                    self._replace_unit(replace(unit, position=target_tile, hp=new_hp))
                    self._add_effect(target_tile[0]*TILE_SIZE + 4, target_tile[1]*TILE_SIZE - 10, "text", "MERGE!", 10, life=40)
                    self._spawn_particles(target_tile[0]*TILE_SIZE + 8, target_tile[1]*TILE_SIZE + 8, 20, [10, 7, 3, 9])
                    self._trigger_shake(15)
                elif target_terrain == Terrain.BLOOD:
                    new_hp = unit.hp + 15
                    self._replace_unit(replace(unit, position=target_tile, hp=new_hp))
                    self._add_effect(target_tile[0]*TILE_SIZE, target_tile[1]*TILE_SIZE - 8, "text", "+15 (BLOOD!)", 8, life=40)
                    self._spawn_particles(target_tile[0]*TILE_SIZE + 8, target_tile[1]*TILE_SIZE + 8, 15, [8, 14])
                    self._trigger_shake(8)
                    self.terrain_map[target_tile[1]][target_tile[0]] = Terrain.PLAIN
                    self.terrain_lookup[(target_tile[0], target_tile[1])] = "plain"
                else:
                    self._replace_unit(replace(unit, position=target_tile))

            self.move_queue.pop(0)
            self.combat_timer = 0
            if not self.move_queue:
                self.animating = False
                # Callback logic for turn switching or battle checks
                if curr.get("is_enemy"):
                    pass # Enemy turn countdown handles next
                else:
                    self._auto_switch_turn_if_needed()

    def _update_combat_animation(self) -> None:
        if not self.combat_queue:
            return

        self.combat_timer += 1
        curr = self.combat_queue[0]

        # Phase 1: Bump (Frames 0-6)
        if 1 <= self.combat_timer <= 6:
            attacker = curr["attacker"]
            defender = curr["defender"]
            
            if attacker.side == unit_system.Side.PLAYER and 3 <= self.combat_timer <= 6:
                if pyxel.btnp(pyxel.KEY_SPACE) and not curr.get("qte_success"):
                    curr["qte_success"] = True
                    sx, sy = self._map_to_screen_pixel(attacker.position[0], attacker.position[1])
                    self._add_effect(sx, sy - 8, "text", text="PERFECT!", color=10, life=20)
                    try:
                        pyxel.play(0, 1) # simple success sound
                    except Exception:
                        pass
            
            # Direction vector
            dx = defender.position[0] - attacker.position[0]
            dy = defender.position[1] - attacker.position[1]
            dist = (dx**2 + dy**2)**0.5
            if dist > 0:
                # Move slightly towards target
                strength = 6.0 * (self.combat_timer / 6.0)
                self.unit_offsets[attacker.unit_id] = (dx / dist * strength, dy / dist * strength)
        elif 7 <= self.combat_timer <= 12:
            attacker = curr["attacker"]
            # Back to normal soon
            self.unit_offsets[attacker.unit_id] = (0, 0)

        # Phase 2: Impact (Frame 7)
        if self.combat_timer == 7:
            attacker = curr["attacker"]
            defender = curr["defender"]
            damage = curr["damage"]
            is_dead = curr["is_dead"]

            if curr.get("qte_success"):
                self.hit_stop_frames = 15
                if damage > 0:
                    damage = int(damage * 1.5)
                    curr["damage"] = damage
                    is_dead = (defender.hp - damage <= 0)
                    curr["is_dead"] = is_dead
            else:
                self.hit_stop_frames = 4

            # Visual Feedback
            sx, sy = self._map_to_screen_pixel(defender.position[0], defender.position[1])
            cx, cy = sx + TILE_SIZE // 2, sy + TILE_SIZE // 2

            if damage < 0:
                self._add_effect(sx, sy, "flash", color=11, life=6)
                self._spawn_particles(cx, cy, 6, [11, 3, 7])
                self._add_effect(sx, sy - 4, "text", text=f"+{-damage}", color=11, life=40)
                try:
                    pyxel.play(0, 2) # Heal sound
                except Exception:
                    pass
            else:
                self._add_effect(sx, sy, "flash", life=6)
                self._add_effect(sx, sy, "slash", life=5) # Slash effect
                self._trigger_shake(10)
                # Particles
                p_colors = [8, 9, 10] if damage > 0 else [6, 7, 13]
                self._spawn_particles(cx, cy, 5 if damage > 0 else 2, p_colors)
                # Floating text
                txt = f"-{damage}" if damage > 0 else "BLOCK"
                col = 8 if damage > 0 else 7
                self._add_effect(sx, sy - 4, "text", text=txt, color=col, life=30)
                try:
                    pyxel.play(0, 0)
                except Exception:
                    pass

            # Apply Logic
            if is_dead:
                self._remove_unit(defender.unit_id)
                # Death explosion
                d_colors = [8, 2, 10] if defender.side == unit_system.Side.ENEMY else [12, 6, 7]
                self._spawn_particles(cx, cy, 15, d_colors + [7])
            else:
                new_hp = max(0, min(max(100, defender.hp), defender.hp - damage))
                final_pos = defender.position
                knockback_path = curr.get("knockback_path", [])
                
                slam_cx, slam_cy = cx, cy
                
                # Resolve knockback
                if curr["attacker"].unit_type == unit_system.UnitType.MAGE and curr.get("defender_terrain_enum") == unit_system.TerrainType.FOREST:
                    dx, dy = curr["defender"].position
                    self.terrain_map[dy][dx] = unit_system.TerrainType.FIRE
                    self.terrain_lookup[(dx, dy)] = "fire"
                    self._add_effect(dx * TILE_SIZE, dy * TILE_SIZE - 8, "text", text="IGNITE!", color=8, life=40)
                    self._spawn_particles(dx * TILE_SIZE + 8, dy * TILE_SIZE + 8, 15, [8, 10, 9])
                    self._trigger_shake(15)

                for k_pos in knockback_path:
                    slam_sx, slam_sy = self._map_to_screen_pixel(k_pos[0], k_pos[1])
                    slam_cx, slam_cy = slam_sx + TILE_SIZE // 2, slam_sy + TILE_SIZE // 2

                    if not (0 <= k_pos[0] < self.map_width and 0 <= k_pos[1] < self.map_height):
                        new_hp -= 20
                        self._add_effect(slam_sx, slam_sy, "text", text="SLAM!", color=8, life=40)
                        self._trigger_shake(25) # Huge hit-stop/shake
                        break
                    t_type = self.terrain_lookup.get(k_pos, "grass")
                    if t_type in ("mountain", "water"):
                        new_hp -= 20
                        self._add_effect(slam_sx, slam_sy, "text", text="SLAM!", color=8, life=40)
                        self._spawn_particles(slam_cx, slam_cy, 8, [13, 5, 1])
                        self._trigger_shake(25)
                        break
                    occupant = self._unit_at(k_pos)
                    if occupant:
                        new_hp -= 15
                        occ_hp = occupant.hp - 15
                        if occ_hp <= 0:
                            self._remove_unit(occupant.unit_id)
                            self._add_effect(slam_sx, slam_sy, "text", text="CRUSHED!", color=8, life=40)
                        else:
                            self._replace_unit(replace(occupant, hp=occ_hp))
                            self._add_effect(slam_sx, slam_sy, "text", text="CRASH!", color=10, life=40)
                        self._trigger_shake(30) # Bowling effect
                        break
                        
                    final_pos = k_pos
                    
                if new_hp <= 0:
                    self._remove_unit(defender.unit_id)
                    d_colors = [8, 2, 10] if defender.side == unit_system.Side.ENEMY else [12, 6, 7]
                    self._spawn_particles(slam_cx, slam_cy, 20, d_colors + [7])
                else:    
                    self._replace_unit(replace(defender, hp=new_hp, position=final_pos))

        # Phase 3: Finish (Frame 20)
        if self.combat_timer >= 20:
            self.unit_offsets.clear()
            self.combat_queue.pop(0)
            self.combat_timer = 0
            if not self.combat_queue:
                self.animating = False
                self._auto_switch_turn_if_needed()

    def _apply_attack(self, attacker: "unit_system.Unit", defender: "unit_system.Unit") -> None:
        defender_terrain = unit_system.TerrainType(
            self.terrain_map[defender.position[1]][defender.position[0]].name.lower()
        )
        preview = unit_system.preview_combat(attacker, defender, defender_terrain, self.units)
        damage = preview.predicted_damage
        is_dead = (defender.hp - damage <= 0) if damage > 0 else False
        knockback_dist = preview.knockback_dist if damage > 0 else 0
        knockback_path = []
        if knockback_dist > 0:
            dx = defender.position[0] - attacker.position[0]
            dy = defender.position[1] - attacker.position[1]
            if dx != 0: dx = 1 if dx > 0 else -1
            if dy != 0: dy = 1 if dy > 0 else -1
            for i in range(1, knockback_dist + 1):
                knockback_path.append((defender.position[0] + dx * i, defender.position[1] + dy * i))

        self.combat_timer = 0
        self.combat_queue.append({
            "attacker": attacker,
            "defender": defender,
            "damage": damage,
            "is_dead": is_dead,
            "knockback_path": knockback_path,
            "defender_terrain_enum": self.terrain_map[defender.position[1]][defender.position[0]]
        })

        if damage < 0:
            self.status_text = f"{attacker.unit_id} healed {defender.unit_id} for {-damage}"
        elif is_dead:
            self.status_text = f"{attacker.unit_id} defeated {defender.unit_id}!"
        else:
            self.status_text = f"{attacker.unit_id} hit {defender.unit_id} for {damage}"

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

    def _save_state(self) -> None:
        state = {
            "units": copy.deepcopy(self.units),
            "terrain_map": copy.deepcopy(self.terrain_map),
            "terrain_lookup": copy.deepcopy(self.terrain_lookup),
            "score": self.score,
            "wave": self.wave,
            "acted_unit_ids": copy.deepcopy(self.acted_unit_ids),
        }
        self.history.append(state)
        if len(self.history) > 10:
            self.history.pop(0)

    def _rewind_time(self) -> None:
        if not self.history:
            return

        # Pop the current state (which is the one we just finished)
        # and then pop the previous state to revert to.
        # This ensures we don't just re-load the current state.
        if len(self.history) > 1:
            self.history.pop() # Remove current state
            prev_state = self.history.pop() # Get the state before that
        else:
            # If only one state, revert to it and clear history
            prev_state = self.history.pop()

        self.units = prev_state["units"]
        self.terrain_map = prev_state["terrain_map"]
        self.terrain_lookup = prev_state["terrain_lookup"]
        self.score = prev_state["score"]
        self.wave = prev_state["wave"]
        self.acted_unit_ids = prev_state["acted_unit_ids"]

        self.current_turn = unit_system.Side.PLAYER # Always rewind to player turn
        self.enemy_acted_unit_ids.clear()
        self.selected_unit_id = None
        self.move_candidates.clear()
        self.attack_candidates.clear()
        self.hovered_unit_id = None
        self.enemy_turn_countdown = 0
        self.winner_side = None
        self.status_text = "Time rewound! Player turn."
        self.glitch_frames = 30 # Visual effect for rewind
        try:
            pyxel.play(0, 0) # Play a sound for rewind
        except Exception:
            pass

    def _start_player_turn(self) -> None:
        self.current_turn = unit_system.Side.PLAYER
        self.status_text = "Player phase..."
        self.acted_unit_ids.clear()
        self._clear_selection()
        self._save_state()
        self._process_terrain_effects(unit_system.Side.PLAYER)

    def _process_terrain_effects(self, side: "unit_system.Side") -> None:
        for i, u in enumerate(self.units):
            if u.hp > 0 and u.side == side:
                terrain_name = self.terrain_lookup.get(u.position)
                
                if u.unit_type == unit_system.UnitType.SLIME:
                    if terrain_name in ["fire", "blood", "forest"]:
                        new_hp = min(200, u.hp + 20)
                        x, y = u.position
                        self.terrain_map[y][x] = Terrain.PLAIN
                        self.terrain_lookup[(x, y)] = "plain"
                        
                        self._replace_unit(replace(u, hp=new_hp))
                        self._add_effect(x*TILE_SIZE, y*TILE_SIZE - 8, "text", f"ATE {terrain_name.upper()}!", 11)
                        self._spawn_particles(x*TILE_SIZE + 8, y*TILE_SIZE + 8, 15, [11, 3, 5])
                        self._trigger_shake(5)
                        try:
                            pyxel.play(0, 2)
                        except Exception:
                            pass
                        continue

                if terrain_name == "fire":
                    new_hp = u.hp - 10
                    if new_hp <= 0:
                        self._remove_unit(u.unit_id)
                        self._add_effect(u.position[0]*TILE_SIZE, u.position[1]*TILE_SIZE - 8, "text", "BURNED!", 8)
                    else:
                        self._replace_unit(replace(u, hp=new_hp))
                        self._add_effect(u.position[0]*TILE_SIZE, u.position[1]*TILE_SIZE - 8, "text", "-10 (FIRE)", 8)
                        self._spawn_particles(u.position[0]*TILE_SIZE + 8, u.position[1]*TILE_SIZE + 8, 8, [8,10,9])
                    self._trigger_shake(10)

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
            if unit.position in attack_tiles and unit.hp > 0
        ]
        if not targets:
            return False

        if enemy_unit.unit_type == unit_system.UnitType.HEALER:
            target = min(targets, key=lambda u: u.hp)
        else:
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

        self.combat_timer = 0
        self.move_queue.append({
            "unit_id": enemy_unit.unit_id,
            "start_tile": enemy_unit.position,
            "target_tile": best_tile,
            "is_enemy": True
        })
        self.animating = True

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
        if pyxel.btnp(pyxel.KEY_R):
            if not self.history:
                self.status_text = "No history to rewind!"
                return
            self._rewind_time()
            return

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
        self.acted_unit_ids.add(unit.unit_id)
        self.status_text = f"{unit.unit_id} moving to {target}"
        try:
            pyxel.play(1, 1) # Move sound
        except Exception:
            pass

        self.animating = True
        self.combat_timer = 0
        self.move_queue.append({
            "unit_id": unit.unit_id,
            "start_tile": unit.position,
            "target_tile": target,
            "is_enemy": False
        })

        self._clear_selection()

    def _execute_attack(self, attacker: "unit_system.Unit", defender: "unit_system.Unit") -> None:
        self._apply_attack(attacker, defender)
        self.acted_unit_ids.add(attacker.unit_id)
        self._clear_selection()
        # Turn switching is now handled by animation end if animating
        if not self.animating:
            self._auto_switch_turn_if_needed()

    # REMOVE duplicate _apply_attack below (Old implementation)

    def _auto_switch_turn_if_needed(self) -> None:
        if self.state == GameState.GAME_OVER or self.current_turn != unit_system.Side.PLAYER:
            return
        if has_unacted_units(self.units, unit_system.Side.PLAYER, self.acted_unit_ids):
            return
        self._switch_to_enemy_turn(manual=False)

    def _switch_to_enemy_turn(self, manual: bool) -> None:
        if self.state == GameState.GAME_OVER:
            return
        self._clear_selection()
        self.current_turn = unit_system.Side.ENEMY
        self.enemy_turn_countdown = ENEMY_TURN_DELAY_FRAMES
        self.enemy_acted_unit_ids.clear()
        self._process_terrain_effects(unit_system.Side.ENEMY)
        if manual:
            self.status_text = "Player ended turn manually"
        else:
            self.status_text = "All units acted; enemy turn"

    def _start_next_wave(self) -> None:
        self.wave += 1
        player_hp_sum = sum(u.hp for u in self.units if u.side == unit_system.Side.PLAYER)
        self.score += int((self.wave - 1) * 100 * (1.0 + player_hp_sum / 500.0))
        self.status_text = f"Wave {self.wave} Started!"
        try:
            pyxel.play(2, 2)
        except Exception:
            pass

        for i, u in enumerate(self.units):
            if u.side == unit_system.Side.PLAYER:
                self.units[i] = replace(u, hp=max(100, u.hp))

        import random
        enemy_count = min(12, 3 + self.wave)
        enemy_types = [
            unit_system.UnitType.SPEAR,
            unit_system.UnitType.CAVALRY,
            unit_system.UnitType.ARCHER,
            unit_system.UnitType.MAGE,
            unit_system.UnitType.HEALER,
            unit_system.UnitType.SLIME,
        ]

        occupied = {u.position for u in self.units}
        spawn_x_min = self.map_width // 2
        for i in range(enemy_count):
            e_type = random.choice(enemy_types)
            for _ in range(50):
                rx = random.randint(spawn_x_min, self.map_width - 1)
                ry = random.randint(0, self.map_height - 1)
                tt = self.terrain_lookup.get((rx, ry), "grass")
                if tt in ("mountain", "water"): continue
                
                if (rx, ry) not in occupied:
                    occupied.add((rx, ry))
                    hp_bonus = (self.wave - 1) * 10
                    self.units.append(
                        unit_system.Unit(f"e_w{self.wave}_{i}", unit_system.Side.ENEMY, e_type, (rx, ry), hp=100 + hp_bonus)
                    )
                    break
                    
        self.current_turn = unit_system.Side.PLAYER
        self.acted_unit_ids.clear()
        self.enemy_acted_unit_ids.clear()
        self._clear_selection()

    def _check_battle_end(self) -> bool:
        if self.state == GameState.GAME_OVER:
            return True

        player_lord_alive = self._unit_by_id(PLAYER_COMMANDER_ID) is not None
        if not player_lord_alive:
            self.state = GameState.GAME_OVER
            self.enemy_turn_countdown = 30 # Use as cooldown before click allowed
            self._clear_selection()
            self.winner_side = unit_system.Side.ENEMY
            self.status_text = "Defeat: your commander was defeated"
            return True

        enemy_alive = any(u.side == unit_system.Side.ENEMY for u in self.units)
        if not enemy_alive:
            self._start_next_wave()
            return False

        return False

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
        unit = self._unit_by_id(unit_id)
        if unit:
            dx, dy = unit.position
            self.terrain_map[dy][dx] = Terrain.BLOOD
            self.terrain_lookup[(dx, dy)] = "blood"
        self.units = [u for u in self.units if u.unit_id != unit_id]
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
        return map_x * TILE_SIZE - int(self.camera_x + self.shake_x), map_y * TILE_SIZE - int(self.camera_y + self.shake_y)

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

        # Apply screen shake to coordinates
        cam_x = self.camera_x + self.shake_x
        cam_y = self.camera_y + self.shake_y

        start_tile_x = int(cam_x // TILE_SIZE)
        start_tile_y = int(cam_y // TILE_SIZE)
        offset_x = -int(cam_x % TILE_SIZE)
        offset_y = -int(cam_y % TILE_SIZE)

        if self.state in (GameState.PLAYING, GameState.GAME_OVER):
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
            self._draw_effects()
            self._draw_battle_result()
            if getattr(self, "glitch_frames", 0) > 0:
                self._draw_glitch()
        elif self.state == GameState.TITLE:
            self._draw_title()

    def _draw_glitch(self) -> None:
        import random
        for _ in range(self.glitch_frames // 2 + 1):
            y = random.randint(0, SCREEN_HEIGHT)
            h = random.randint(1, 4)
            color = random.choice([0, 1, 2, 5, 8, 11])
            pyxel.rect(0, y, SCREEN_WIDTH, h, color)
        if self.glitch_frames % 2 == 0:
            shift_y = random.randint(0, SCREEN_HEIGHT)
            shift_h = random.randint(10, 30)
            pyxel.rect(0, shift_y, SCREEN_WIDTH, shift_h, random.choice([1, 2, 5]))

    def _draw_effects(self) -> None:
        for eff in self.effects:
            if eff.type == "text":
                self._draw_text(int(eff.x), int(eff.y), eff.text, eff.color, compact=True)
            elif eff.type == "flash":
                # Flicker effect based on life
                if (eff.life // 2) % 2 == 0:
                    pyxel.rect(int(eff.x), int(eff.y), TILE_SIZE, TILE_SIZE, 7)
            elif eff.type == "slash":
                # Draw a simple slash arc or line
                cx, cy = int(eff.x) + TILE_SIZE//2, int(eff.y) + TILE_SIZE//2
                offset = 6 - eff.life
                pyxel.line(cx - 6 + offset, cy - 6 - offset, cx + 6 + offset, cy + 6 - offset, 7)
                if eff.life > 2:
                    pyxel.line(cx - 5 + offset, cy - 6 - offset, cx + 7 + offset, cy + 6 - offset, 10)

        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

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

            # Apply unit-specific animation offset
            ox, oy = self.unit_offsets.get(unit.unit_id, (0, 0))
            sx += int(ox)
            sy += int(oy)

            if sx <= -TILE_SIZE or sy <= -TILE_SIZE or sx >= SCREEN_WIDTH or sy >= SCREEN_HEIGHT:
                continue

            u_type = unit.unit_type
            u_side = unit.side
            
            u_x = 0
            u_y = 16 if u_side == unit_system.Side.PLAYER else 32
            
            u_x = 0
            if u_type == unit_system.UnitType.SPEAR:
                u_x = 0
            elif u_type == unit_system.UnitType.CAVALRY:
                u_x = 16
            elif u_type == unit_system.UnitType.ARCHER:
                u_x = 32
            elif u_type == unit_system.UnitType.MAGE:
                u_x = 32
            elif u_type == unit_system.UnitType.HEALER:
                u_x = 0

            if u_type != unit_system.UnitType.SLIME:
                pyxel.blt(sx, sy, 0, u_x, u_y, 16, 16, 0)
                if u_type == unit_system.UnitType.MAGE:
                    pyxel.text(sx + 10, sy + 6, "m", 8)
                elif u_type == unit_system.UnitType.HEALER:
                    pyxel.text(sx + 10, sy + 6, "h", 11)
            else:
                sc = 11 if u_side == unit_system.Side.PLAYER else 3
                pyxel.rect(sx + 4, sy + 8, 8, 6, sc)
                pyxel.rect(sx + 3, sy + 10, 10, 4, sc)
                pyxel.rect(sx + 5, sy + 6, 6, 2, sc)
                pyxel.pset(sx + 6, sy + 8, 0)
                pyxel.pset(sx + 9, sy + 8, 0)

            if unit.side == unit_system.Side.PLAYER and unit.unit_id in self.acted_unit_ids:
                # Dim the unit
                pyxel.rect(sx, sy, 16, 16, 5) # Draw semi-transparent rect or use pal? Pal is better but here just a rect overlay is simple
                
            # Floating HP Bar
            hp_ratio = min(1.0, unit.hp / 100)
            bar_color = 11 if unit.side == unit_system.Side.PLAYER else 8
            pyxel.rect(sx, sy - 3, 16, 2, 0)
            pyxel.rect(sx, sy - 3, int(16 * hp_ratio), 2, bar_color)
            if unit.hp > 100:
                over_ratio = min(1.0, (unit.hp - 100) / 400) # Since max is 500
                over_col = 10 if unit.side == unit_system.Side.PLAYER else 9
                pyxel.rect(sx, sy - 2, int(16 * over_ratio), 1, over_col)
            
            # Action status indicator
            if unit.unit_id not in self.acted_unit_ids and unit.side == self.current_turn:
                # tiny green dot for "ready"
                pyxel.pset(sx + 14, sy - 3, 11)

            if unit.unit_id == self.selected_unit_id:
                pyxel.rectb(sx, sy, TILE_SIZE, TILE_SIZE, 7)

    def _draw_top_bar(self) -> None:
        # Semi-transparent background (stipple pattern)
        for y in range(TOP_BAR_HEIGHT):
            for x in range(SCREEN_WIDTH):
                if (x + y) % 2 == 0:
                    pyxel.pset(x, y, 0)
                else:
                    pyxel.pset(x, y, 1)
        pyxel.line(0, TOP_BAR_HEIGHT, SCREEN_WIDTH, TOP_BAR_HEIGHT, 5) # Border

        turn_text = "TURN: PLAYER" if self.current_turn == unit_system.Side.PLAYER else "TURN: ENEMY"
        
        # Text shadow for better readability
        self._draw_text(5, 5, turn_text, 0, compact=True)
        self._draw_text(4, 4, turn_text, 7, compact=True)

        wave_score_text = f"WAVE: {self.wave} | SCORE: {self.score}"
        self._draw_text(61, 5, wave_score_text, 0, compact=True)
        self._draw_text(60, 4, wave_score_text, 10, compact=True)

        button_x, button_y, button_w, button_h = END_TURN_BUTTON
        button_color = 2 if (self.current_turn == unit_system.Side.PLAYER) else 5
        pyxel.rect(button_x, button_y, button_w, button_h, button_color)
        pyxel.rectb(button_x, button_y, button_w, button_h, 7)
        self._draw_text(button_x + 8, button_y + 3, "End Turn", 7, compact=True)

    def _draw_bottom_bar(self) -> None:
        # Semi-transparent background
        for y in range(SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT, SCREEN_HEIGHT):
            for x in range(SCREEN_WIDTH):
                if (x + y) % 2 == 0:
                    pyxel.pset(x, y, 0)
                else:
                    pyxel.pset(x, y, 1)
        pyxel.line(0, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT - 1, SCREEN_WIDTH, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT - 1, 5)

        self._draw_text(5, SCREEN_HEIGHT - 8, self.status_text[:56], 0, compact=True)
        self._draw_text(4, SCREEN_HEIGHT - 9, self.status_text[:56], 7, compact=True)

    def _draw_hover_unit_info(self) -> None:
        hovered_tile = self._screen_to_map_tile(pyxel.mouse_x, pyxel.mouse_y)
        if hovered_tile is None:
            return

        unit = self._unit_at(hovered_tile)
        terrain = self.terrain_map[hovered_tile[1]][hovered_tile[0]]
        
        selected_unit = self._unit_by_id(self.selected_unit_id)
        is_attack_preview = (
            selected_unit and 
            unit and 
            unit.side != selected_unit.side and 
            hovered_tile in self.attack_candidates
        )
        
        lines = []
        if unit:
            stats = unit_system.get_unit_stats(unit.unit_type)
            side_label = "玩家" if unit.side == unit_system.Side.PLAYER else "敌军"
            lines.extend([
                f"[{unit.unit_id}] {side_label}",
                f"HP: {unit.hp} | {unit.unit_type.value.upper()}",
                f"ATK/DEF: {stats.attack}/{stats.defense}",
                f"MOV/RNG: {stats.movement} | {stats.min_range}-{stats.max_range}",
            ])
            
        lines.append(f"地形: {terrain.name}")
        terrain_type = unit_system.TerrainType(terrain.name.lower())
        def_bonus = unit_system.terrain_defense_bonus(terrain_type)
        if def_bonus > 0:
            lines.append(f"地形防御: +{def_bonus}")
            
        if is_attack_preview and unit is not None:
            lines.append("--- 战斗预测 ---")
            preview = unit_system.preview_combat(selected_unit, unit, terrain_type, self.units)
            if preview.predicted_damage < 0:
                lines.append(f"预计治疗: {-preview.predicted_damage}")
            else:
                lines.append(f"预计伤害: {preview.predicted_damage}")
            lines.append(f"克制倍率: {preview.attacker_multiplier}x")

        box_w = 142
        box_h = len(lines) * 11 + 8
        box_x = min(max(pyxel.mouse_x + 8, 2), SCREEN_WIDTH - box_w - 2)
        box_y = min(max(pyxel.mouse_y + 8, TOP_BAR_HEIGHT + 1), SCREEN_HEIGHT - box_h - BOTTOM_BAR_HEIGHT)

        compact = True

        pyxel.rect(box_x, box_y, box_w, box_h, 1)
        pyxel.rectb(box_x, box_y, box_w, box_h, 7 if not is_attack_preview else 8)
        
        for i, line in enumerate(lines):
            color = 7
            if "战斗预测" in line: color = 8
            elif "预计伤害" in line: color = 10
            elif "克制" in line and "1.25" in line: color = 11
            elif "克制" in line and "0.75" in line: color = 8
            elif "地形防御" in line: color = 11
            self._draw_text(box_x + 4, box_y + 4 + i * 11, line, color, compact=compact)

    def _draw_terrain_tile(self, x: int, y: int, terrain: Terrain) -> None:
        t_x = 0
        t_y = 0
        if terrain == Terrain.PLAIN:
            t_x = 0
        elif terrain == Terrain.FOREST:
            t_x = 16
        elif terrain == Terrain.RIVER:
            t_x = 32
        elif terrain == Terrain.SEA:
            t_x = 48
            
        pyxel.blt(x, y, 0, t_x, t_y, 16, 16)

    def _draw_title(self) -> None:
        title_text = "Pyxel Strategy Demo"
        start_text = "- Click to Start -"
        
        # Simple animated background for title
        for i in range(50):
            pyxel.pset(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), random.choice([1, 5, 13]))

        # Shadow and Title
        self._draw_text(SCREEN_WIDTH//2 - len(title_text)*4 + 2, SCREEN_HEIGHT//2 - 20 + 2, title_text, 0)
        self._draw_text(SCREEN_WIDTH//2 - len(title_text)*4, SCREEN_HEIGHT//2 - 20, title_text, 10)

        # Blinking start text
        if (pyxel.frame_count // 15) % 2 == 0:
            self._draw_text(SCREEN_WIDTH//2 - len(start_text)*3 + 2, SCREEN_HEIGHT//2 + 10 + 2, start_text, 0, compact=True)
            self._draw_text(SCREEN_WIDTH//2 - len(start_text)*3, SCREEN_HEIGHT//2 + 10, start_text, 7, compact=True)

    def _draw_battle_result(self) -> None:
        if self.state != GameState.GAME_OVER:
            return

        box_w = 160
        box_h = 60
        box_x = (SCREEN_WIDTH - box_w) // 2
        box_y = (SCREEN_HEIGHT - box_h) // 2
        
        # Semi-transparent overlay for the whole screen
        for y in range(SCREEN_HEIGHT):
            for x in range(SCREEN_WIDTH):
                if (x + y) % 2 == 0:
                    pyxel.pset(x, y, 0)

        pyxel.rect(box_x, box_y, box_w, box_h, 0)
        
        is_victory = self.winner_side == unit_system.Side.PLAYER
        result_color = 11 if is_victory else 8
        pyxel.rectb(box_x, box_y, box_w, box_h, result_color)
        pyxel.rectb(box_x+1, box_y+1, box_w-2, box_h-2, result_color)

        result_text = "VICTORY!" if is_victory else "DEFEAT"
        self._draw_text(box_x + box_w//2 - len(result_text)*4, box_y + 16, result_text, result_color)
        
        if self.enemy_turn_countdown <= 0:
            prompt = "Click or Space to Title"
            self._draw_text(box_x + box_w//2 - len(prompt)*3, box_y + 40, prompt, 7, compact=True)


if __name__ == "__main__":
    Game()
