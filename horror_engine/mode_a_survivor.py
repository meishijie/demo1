import pyxel
import math
import random
from horror_engine.helpers import clamp, distance, ParticleSystem, FloatingTextSystem, ScreenShake

class ExpGem:
    def __init__(self, x: float, y: float, value: int = 1):
        self.x = x
        self.y = y
        self.value = value

class Enemy:
    def __init__(self, x: float, y: float, hp: float = 10.0, speed: float = 0.4):
        self.x = x
        self.y = y
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.damage = 10.0
        self.hit_by_pulses = set()

    def update(self, px: float, py: float):
        angle = math.atan2(py - self.y, px - self.x)
        self.x += math.cos(angle) * self.speed
        self.y += math.sin(angle) * self.speed

class EliteGuard:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.speed = 0.6
        self.light_radius = 45.0

    def update(self, px: float, py: float):
        angle = math.atan2(py - self.y, px - self.x)
        self.x += math.cos(angle) * self.speed
        self.y += math.sin(angle) * self.speed

class Tree:
    def __init__(self, x: float, y: float, radius: float = 16.0):
        self.x = x
        self.y = y
        self.radius = radius

class SonarPulse:
    def __init__(self, x: float, y: float, max_radius: float, speed: float, damage: float, pulse_id: int):
        self.x = x
        self.y = y
        self.radius = 0.0
        self.max_radius = max_radius
        self.speed = speed
        self.damage = damage
        self.pulse_id = pulse_id
        self.active = True

    def update(self):
        self.radius += self.speed
        if self.radius >= self.max_radius:
            self.active = False

class Player:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.speed = 1.0
        self.max_hp = 100.0
        self.hp = 100.0
        self.level = 1
        self.exp = 0
        self.exp_to_next = 10
        self.sonar_timer = 0
        self.sonar_cooldown = 120 # frames
        self.sonar_damage = 5.0
        self.sonar_radius = 60.0
        self.magnet_radius = 40.0
        self.is_moving = False
        self.is_holding_breath = False

    def update(self):
        dx, dy = 0.0, 0.0
        if pyxel.btn(pyxel.KEY_W) or pyxel.btn(pyxel.KEY_UP): dy -= 1
        if pyxel.btn(pyxel.KEY_S) or pyxel.btn(pyxel.KEY_DOWN): dy += 1
        if pyxel.btn(pyxel.KEY_A) or pyxel.btn(pyxel.KEY_LEFT): dx -= 1
        if pyxel.btn(pyxel.KEY_D) or pyxel.btn(pyxel.KEY_RIGHT): dx += 1
        
        # Spacebar to hold breath
        self.is_holding_breath = pyxel.btn(pyxel.KEY_SPACE)

        self.is_moving = False
        if (dx != 0 or dy != 0) and not self.is_holding_breath:
            self.is_moving = True
            length = math.hypot(dx, dy)
            self.x += (dx / length) * self.speed
            self.y += (dy / length) * self.speed

        self.sonar_timer += 1

class ModeASurvivor:
    def __init__(self, font: pyxel.Font | None):
        self.font = font
        self.state = "PLAY"
        
        self.map_w = 1200
        self.map_h = 1200
        self.player = Player(self.map_w / 2, self.map_h / 2)
        
        self.trees = []
        for _ in range(40):
            self.trees.append(Tree(random.uniform(50, self.map_w - 50), random.uniform(50, self.map_h - 50), random.uniform(15, 25)))

        self.enemies = []
        self.gems = []
        self.pulses = []
        self.pulse_counter = 0
        self.elite_guard = EliteGuard(100, 100) # Spawn far away initially

        self.camera_x = 0
        self.camera_y = 0

        # Eye Mechanic
        self.eye_state = "CLOSED" # CLOSED, OPENING, OPEN
        self.eye_timer = 0

        # Juice Systems
        self.particles = ParticleSystem()
        self.texts = FloatingTextSystem()
        self.shake = ScreenShake()

        # Upgrade choices
        self.choices = []

    def spawn_enemy(self):
        # Spawn outside camera view
        angle = random.uniform(0, math.pi * 2)
        dist = random.uniform(200, 300)
        ex = self.player.x + math.cos(angle) * dist
        ey = self.player.y + math.sin(angle) * dist
        # constrain to map
        ex = clamp(ex, 0, self.map_w)
        ey = clamp(ey, 0, self.map_h)
        self.enemies.append(Enemy(ex, ey, hp=10.0 + self.player.level * 2, speed=0.3 + random.uniform(0, 0.2)))

    def update_play(self) -> str:
        self.shake.update()
        self.particles.update()
        self.texts.update()
        
        self.player.update()
        self.player.x = clamp(self.player.x, 0, self.map_w)
        self.player.y = clamp(self.player.y, 0, self.map_h)

        if self.player.is_moving and pyxel.frame_count % 5 == 0:
            self.particles.emit(self.player.x, self.player.y + 4, 1, [13, 5, 1], 0.5, 15)

        # Eye Logic
        self.eye_timer += 1
        if self.eye_state == "CLOSED" and self.eye_timer > 600:
            self.eye_state = "OPENING"
            self.eye_timer = 0
        elif self.eye_state == "OPENING" and self.eye_timer > 120:
            self.eye_state = "OPEN"
            self.eye_timer = 0
        elif self.eye_state == "OPEN":
            # Check player visibility
            in_shadow = False
            for t in self.trees:
                if distance(self.player.x, self.player.y, t.x, t.y) <= t.radius + 10:
                    in_shadow = True
                    break
            
            if self.player.is_moving or not in_shadow or not self.player.is_holding_breath:
                self.player.hp -= 0.5 # Huge damage over time
                self.shake.add_shake(2.0)
                
            if self.eye_timer > 180:
                self.eye_state = "CLOSED"
                self.eye_timer = 0

        # Camera follow
        target_cx = self.player.x - 128
        target_cy = self.player.y - 128
        self.camera_x += (target_cx - self.camera_x) * 0.1
        self.camera_y += (target_cy - self.camera_y) * 0.1
        self.camera_x = clamp(self.camera_x, 0, self.map_w - 256)
        self.camera_y = clamp(self.camera_y, 0, self.map_h - 256)

        # Weapon logic
        if self.player.sonar_timer >= self.player.sonar_cooldown:
            self.player.sonar_timer = 0
            self.pulse_counter += 1
            self.pulses.append(SonarPulse(
                self.player.x, self.player.y, 
                self.player.sonar_radius, 2.0, self.player.sonar_damage, self.pulse_counter
            ))
            self.shake.add_shake(1.0) # subtle boom

        # Update Pulses
        for p in self.pulses:
            p.update()
        self.pulses = [p for p in self.pulses if p.active]

        # Spawn logic
        if pyxel.frame_count % max(10, 60 - self.player.level * 2) == 0:
            self.spawn_enemy()

        # Update Enemies & Collisions
        for e in self.enemies:
            e.update(self.player.x, self.player.y)
            
            # Pulse collision
            for p in self.pulses:
                if p.pulse_id not in e.hit_by_pulses:
                    dist = distance(e.x, e.y, p.x, p.y)
                    # If enemy is inside the expanding ring (thickness 10)
                    if dist <= p.radius and dist > p.radius - 10:
                        e.hp -= p.damage
                        e.hit_by_pulses.add(p.pulse_id)

            # Player collision
            if distance(e.x, e.y, self.player.x, self.player.y) < 8:
                self.player.hp -= e.damage * 0.016 # continuous contact damage
                self.shake.add_shake(0.5)

        # Update Elite Guard
        self.elite_guard.update(self.player.x, self.player.y)
        if distance(self.elite_guard.x, self.elite_guard.y, self.player.x, self.player.y) < self.elite_guard.light_radius:
            self.player.hp -= 0.2
            self.shake.add_shake(1.5)

        # Death
        dead_enemies = [e for e in self.enemies if e.hp <= 0]
        for e in dead_enemies:
            self.gems.append(ExpGem(e.x, e.y))
            self.particles.emit(e.x, e.y, 8, [8, 2, 14], 1.5, 20)
            self.texts.emit(e.x, e.y - 10, "KILL", 8, 20)
            
        self.enemies = [e for e in self.enemies if e.hp > 0]
        
        for d in dead_enemies:
            self.gems.append(ExpGem(d.x, d.y, 1))

        # Gems
        collected = []
        for g in self.gems:
            dist = distance(g.x, g.y, self.player.x, self.player.y)
            if dist < self.player.magnet_radius:
                # pull
                angle = math.atan2(self.player.y - g.y, self.player.x - g.x)
                g.x += math.cos(angle) * 3.0
                g.y += math.sin(angle) * 3.0
                if dist < 6:
                    collected.append(g)
        
        for g in collected:
            self.player.exp += g.value
            self.particles.emit(g.x, g.y, 4, [11, 10, 3], 1.0, 15)
            self.texts.emit(g.x, g.y - 5, "+EXP", 11, 30)
            g.value = 0
        
        self.gems = [g for g in self.gems if g.value > 0]

        # Level Up
        if self.player.exp >= self.player.exp_to_next:
            self.player.exp -= self.player.exp_to_next
            self.player.level += 1
            self.player.exp_to_next = int(self.player.exp_to_next * 1.5)
            self.state = "LEVEL_UP"
            self.generate_choices()

        if self.player.hp <= 0:
            self.state = "GAME_OVER"

        return "RUNNING"

    def generate_choices(self):
        self.choices = [
            {"name": "声呐增强", "desc": "伤害+3, 半径+10", "type": "sonar_amp"},
            {"name": "频率提升", "desc": "冷却减少 15%", "type": "sonar_cd"},
            {"name": "恢复生命", "desc": "恢复 30 HP", "type": "heal"},
        ]

    def update_levelup(self) -> str:
        if pyxel.btnp(pyxel.KEY_1) and len(self.choices) >= 1:
            self.apply_choice(self.choices[0])
        elif pyxel.btnp(pyxel.KEY_2) and len(self.choices) >= 2:
            self.apply_choice(self.choices[1])
        elif pyxel.btnp(pyxel.KEY_3) and len(self.choices) >= 3:
            self.apply_choice(self.choices[2])
        return "RUNNING"

    def apply_choice(self, choice):
        ctype = choice["type"]
        if ctype == "sonar_amp":
            self.player.sonar_damage += 3.0
            self.player.sonar_radius += 10.0
        elif ctype == "sonar_cd":
            self.player.sonar_cooldown = max(10, int(self.player.sonar_cooldown * 0.85))
        elif ctype == "heal":
            self.player.hp = min(self.player.max_hp, self.player.hp + 30.0)
        self.state = "PLAY"

    def update(self) -> str:
        if pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_Q):
            return "QUIT_TO_MENU"

        if self.state == "PLAY":
            return self.update_play()
        elif self.state == "LEVEL_UP":
            return self.update_levelup()
        elif self.state == "GAME_OVER":
            if pyxel.btnp(pyxel.KEY_R):
                # Reset
                self.__init__(self.font)
            return "RUNNING"
            
        return "RUNNING"
        
    def draw_play(self):
        pyxel.cls(0)
        
        ox, oy = self.shake.get_offset()
        cx = self.camera_x + ox
        cy = self.camera_y + oy

        # Background tint for Eye
        if self.eye_state == "OPEN":
            pyxel.rect(0, 0, 256, 256, 8) # faint red tint via dither?
            # Pyxel doesn't have true alpha, so let's just make background 2
            pyxel.cls(2)
        elif self.eye_state == "OPENING":
            pyxel.cls(13)

        # Draw grid for map reference
        start_x = int(cx / 32) * 32
        start_y = int(cy / 32) * 32
        for x in range(start_x, int(cx) + 256, 32):
            pyxel.line(x - cx, 0, x - cx, 256, 1)
        for y in range(start_y, int(cy) + 256, 32):
            pyxel.line(0, y - cy, 256, y - cy, 1)

        # Draw Trees
        for t in self.trees:
            sx, sy = t.x - cx, t.y - cy
            # shadow
            pyxel.elli(sx-t.radius+2, sy+t.radius//2 - 2, t.radius*2-4, t.radius, 1)
            # trunk
            pyxel.rect(sx-3, sy-t.radius//2, 6, t.radius, 4)
            # leaves base
            pyxel.circ(sx, sy-t.radius//2, t.radius, 3)
            # leaves highlight
            pyxel.circ(sx - t.radius//4, sy-t.radius//2 - t.radius//4, t.radius//2, 11)
            # outline
            pyxel.circb(sx, sy-t.radius//2, t.radius, 0)

        # Elite Guard
        sx, sy = self.elite_guard.x - cx, self.elite_guard.y - cy
        # Shadow
        pyxel.elli(sx-6, sy+8, 12, 4, 1)
        # Cloak body
        bob = math.sin(pyxel.frame_count * 0.1) * 3
        sy += bob
        pyxel.rect(sx - 5, sy - 10, 10, 20, 0)
        pyxel.rect(sx - 4, sy - 9, 8, 18, 5) # inner cloak color
        # Lantern light ring
        pyxel.circb(sx, sy, self.elite_guard.light_radius, 10)
        # Lantern core
        pyxel.circ(sx, sy, 4, 10)
        pyxel.circ(sx, sy, 2, 7)
        
        # Map bounds
        pyxel.rectb(0 - cx, 0 - cy, self.map_w, self.map_h, 8)

        # Gems
        for g in self.gems:
            sx, sy = g.x - cx, g.y - cy
            bob = math.sin(pyxel.frame_count * 0.2 + g.x) * 2
            sy += bob
            pyxel.rect(sx - 1, sy, 3, 1, 11)
            pyxel.rect(sx, sy - 1, 1, 3, 11)
            pyxel.pset(sx, sy, 7) # shiny core

        # Pulses
        for p in self.pulses:
            sx, sy = p.x - cx, p.y - cy
            pyxel.circb(sx, sy, p.radius, 12)

        # Enemies
        for e in self.enemies:
            sx, sy = e.x - cx, e.y - cy
            bob = math.sin(pyxel.frame_count * 0.3 + e.x) * 2
            pyxel.elli(sx-3, sy+3, 6, 2, 1) # Shadow
            sy += bob
            pyxel.rect(sx - 3, sy - 3, 6, 6, 8) # Body
            pyxel.rectb(sx - 3, sy - 3, 6, 6, 0) # border
            pyxel.pset(sx - 1, sy - 1, 7) # Eye
            pyxel.pset(sx + 1, sy - 1, 7) # Eye
            # HP bar
            hp_w = max(0, int((e.hp / e.max_hp) * 6))
            pyxel.rect(sx - 3, sy - 5, hp_w, 1, 8)

        # Player
        sx = self.player.x - cx
        sy = self.player.y - cy
        color = 9
        if self.player.is_holding_breath:
            color = 5
            
        bob = math.sin(pyxel.frame_count * 0.5) * 2 if self.player.is_moving else 0
        # Shadow
        pyxel.elli(sx-4, sy+4, 8, 3, 1)
        sy += bob
        pyxel.rect(sx - 4, sy - 4, 8, 8, color)
        pyxel.rectb(sx - 4, sy - 4, 8, 8, 0) # outline
        pyxel.rect(sx - 2, sy - 2, 1, 2, 7) # Left eye
        pyxel.rect(sx + 1, sy - 2, 1, 2, 7) # Right eye
        
        # magnet
        pyxel.circb(sx, sy, self.player.magnet_radius, 1)
        
        # Juice Top Layer
        self.particles.draw(cx, cy)
        self.texts.draw(self.font, cx, cy)

        # UI: Eye Status
        if self.eye_state == "OPEN":
            pyxel.rect(96, 8, 100, 14, 0)
            if self.font:
                pyxel.text(100, 10, "巨眼注视!! 屏息掩蔽!", 8, self.font)
            else:
                pyxel.text(100, 10, "EYE OPEN! HIDE!", 8)
        elif self.eye_state == "OPENING":
            pyxel.rect(96, 8, 80, 14, 0)
            if self.font:
                pyxel.text(100, 10, "天空变色...", 10, self.font)

        # HUD
        pyxel.rect(2, 2, 50, 14, 0)
        if self.font:
            pyxel.text(5, 5, f"LV: {self.player.level}", 7, self.font)
        else:
            pyxel.text(5, 5, f"LV: {self.player.level}", 7)
        
        # Exp bar
        pyxel.rect(0, 0, 256, 3, 1)
        exp_w = int((self.player.exp / self.player.exp_to_next) * 256)
        pyxel.rect(0, 0, exp_w, 3, 11)

        # HP bar (Player)
        pyxel.rect(5, 15, 100, 5, 1)
        hp_w = int((self.player.hp / self.player.max_hp) * 100)
        pyxel.rect(5, 15, hp_w, 5, 8 if hp_w < 30 else 3)
        pyxel.rectb(5, 15, 100, 5, 0)

    def draw_levelup(self):
        self.draw_play() # Background
        pyxel.rect(28, 40, 200, 160, 0)
        pyxel.rectb(28, 40, 200, 160, 7)
        
        if self.font:
            pyxel.text(90, 50, "升 级 ! (LEVEL UP)", 10, self.font)
            for i, c in enumerate(self.choices):
                y = 80 + i * 40
                pyxel.text(40, y, f"[{i+1}] {c['name']}", 7, self.font)
                pyxel.text(55, y+10, c['desc'], 13, self.font)
        else:
            pyxel.text(90, 50, "LEVEL UP", 10)
            for i, c in enumerate(self.choices):
                y = 80 + i * 40
                pyxel.text(40, y, f"[{i+1}] {c['name']}", 7)

    def draw_gameover(self):
        self.draw_play()
        pyxel.rect(0, 100, 256, 50, 0)
        if self.font:
            pyxel.text(100, 110, "死 亡", 8, self.font)
            pyxel.text(80, 130, "按 [R] 重新开始", 7, self.font)
            pyxel.text(80, 145, "按 [Q] 返回菜单", 13, self.font)
        else:
            pyxel.text(100, 110, "YOU DIED", 8)
            pyxel.text(80, 130, "Press [R] to Restart", 7)

    def draw(self) -> None:
        if self.state == "PLAY":
            self.draw_play()
        elif self.state == "LEVEL_UP":
            self.draw_levelup()
        elif self.state == "GAME_OVER":
            self.draw_gameover()
