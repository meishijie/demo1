import pyxel
import random
import math
from horror_engine.helpers import clamp, point_in_rect, ParticleSystem, FloatingTextSystem, ScreenShake

class MiniGameZeroHour:
    def __init__(self, difficulty):
        self.time_limit = max(60, 180 - difficulty * 20)
        self.timer = self.time_limit
        self.points = []
        self.anomaly_idx = random.randint(0, 15)
        for i in range(16):
            x = 40 + (i % 4) * 40
            y = 60 + (i // 4) * 40
            self.points.append({"x": x, "y": y, "is_anomaly": (i == self.anomaly_idx)})
        self.result = None # "WIN" or "LOSE"

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.result = "LOSE"
            return

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            for p in self.points:
                if point_in_rect(mx, my, p["x"]-10, p["y"]-10, 20, 20):
                    if p["is_anomaly"]:
                        self.result = "WIN"
                    else:
                        self.result = "LOSE"
                    return

    def draw(self, font, particles):
        pyxel.cls(0)
        if font:
            pyxel.text(50, 20, f"寻找扭曲点! 剩余时间: {self.timer//30}", 8, font)
        else:
            pyxel.text(50, 20, f"Find Anomaly! Time: {self.timer}", 8)
            
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        for p in self.points:
            color = 7
            if p["is_anomaly"] and pyxel.frame_count % 30 < 5: 
                # slight visual flicker for the anomaly
                color = 13
            
            # Hover tween effect
            rect_ds = 0
            if point_in_rect(mx, my, p["x"]-10, p["y"]-10, 20, 20):
                color = 10
                rect_ds = 2
                
            # Shadow
            pyxel.rect(p["x"]-10 - rect_ds, p["y"]-10 - rect_ds + 3, 20 + rect_ds*2, 20 + rect_ds*2, 1)
            # Body
            pyxel.rect(p["x"]-10 - rect_ds, p["y"]-10 - rect_ds, 20 + rect_ds*2, 20 + rect_ds*2, color)
            pyxel.rectb(p["x"]-10 - rect_ds, p["y"]-10 - rect_ds, 20 + rect_ds*2, 20 + rect_ds*2, 0)
            
            pyxel.pset(p["x"], p["y"], 5)

class MiniGameSignal:
    def __init__(self, difficulty):
        self.freq = 50.0
        self.target = random.uniform(20.0, 80.0)
        self.timer = 300
        self.lock_frames = 0
        self.result = None

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.result = "LOSE"
            return
            
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.freq -= 1.0
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.freq += 1.0

        # drift
        if pyxel.frame_count % 2 == 0:
            self.freq += random.uniform(-2.0, 2.0)
            
        self.freq = clamp(self.freq, 0.0, 100.0)

        diff = abs(self.freq - self.target)
        if diff < 5.0:
            self.lock_frames += 1
            if self.lock_frames >= 60:
                self.result = "WIN"
        else:
            self.lock_frames = max(0, self.lock_frames - 2)

    def draw(self, font, particles):
        pyxel.cls(0)
        if font:
            pyxel.text(40, 30, f"锁定信号! 剩余时间: {self.timer//30}", 8, font)
            pyxel.text(80, 50, f"锁定进度: {self.lock_frames}/60", 11, font)
        
        pyxel.rect(28, 120, 200, 10, 5)
        # target zone
        tx = 28 + (self.target / 100.0) * 200
        pyxel.rect(tx-10, 120, 20, 10, 3)
        
        # current
        cx = 28 + (self.freq / 100.0) * 200
        
        # Sparks when locking
        is_locked = abs(self.freq - self.target) < 5.0
        if is_locked and pyxel.frame_count % 3 == 0:
            particles.emit(cx, 125, 1, [11, 10, 7], 1.0, 10)
            
        pyxel.rect(cx - 2, 110, 4, 30, 10 if is_locked else 8)
        
        # Sine wave across the screen just for visual juice
        for i in range(28, 228, 4):
            wave_y = 100 + math.sin(pyxel.frame_count * 0.1 + i * 0.05) * 5
            pyxel.pset(i, wave_y, 5)

class MiniGameGlitch:
    def __init__(self, difficulty):
        self.seq_len = min(8, 3 + difficulty)
        self.sequence = [random.randint(0, 3) for _ in range(self.seq_len)]
        self.input_idx = 0
        self.preview_timer = 60 * 2 # 2 seconds preview
        self.result = None
        
        self.buttons = [
            {"id": 0, "x": 60, "y": 100},
            {"id": 1, "x": 100, "y": 100},
            {"id": 2, "x": 140, "y": 100},
            {"id": 3, "x": 180, "y": 100}
        ]

    def shuffle_buttons(self):
        positions = [(b["x"], b["y"]) for b in self.buttons]
        random.shuffle(positions)
        for i, b in enumerate(self.buttons):
            b["x"], b["y"] = positions[i]

    def update(self):
        if self.preview_timer > 0:
            self.preview_timer -= 1
            return
            
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            clicked = -1
            for b in self.buttons:
                if point_in_rect(mx, my, b["x"], b["y"], 30, 30):
                    clicked = b["id"]
                    break
            
            if clicked != -1:
                if clicked == self.sequence[self.input_idx]:
                    self.input_idx += 1
                    self.shuffle_buttons()
                    if self.input_idx >= len(self.sequence):
                        self.result = "WIN"
                else:
                    self.result = "LOSE"

    def draw(self, font, particles):
        pyxel.cls(0)
        if self.preview_timer > 0:
            if font:
                pyxel.text(50, 20, "记住序列!!", 8, font)
            for i, val in enumerate(self.sequence):
                pyxel.text(50 + i*15, 50, str(val+1), 10)
        else:
            if font:
                pyxel.text(50, 20, f"输入序列! 进度 {self.input_idx}/{self.seq_len}", 7, font)
        
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        for b in self.buttons:
            rect_ds = 0
            color = 5
            if point_in_rect(mx, my, b["x"], b["y"], 30, 30):
                rect_ds = 2
                color = 10
            # shadow
            pyxel.rect(b["x"] - rect_ds, b["y"] - rect_ds + 3, 30 + rect_ds*2, 30 + rect_ds*2, 1)
            # body
            pyxel.rect(b["x"] - rect_ds, b["y"] - rect_ds, 30 + rect_ds*2, 30 + rect_ds*2, 0)
            pyxel.rectb(b["x"] - rect_ds, b["y"] - rect_ds, 30 + rect_ds*2, 30 + rect_ds*2, color)
            
            if font:
                pyxel.text(b["x"]+10, b["y"]+10, str(b["id"]+1), 7, font)

class ModeBGambler:
    def __init__(self, font: pyxel.Font | None):
        self.font = font
        self.state = "MENU" # MENU, PLAYING, SHOP, GAMEOVER
        
        # Player Stats
        self.round = 1
        self.chips = 0
        self.target_chips = 1000
        self.gold = 0
        
        self.max_hp = 5 # Body parts
        self.hp = 5
        
        # Jokers/Relics
        self.jokers = [] 
        self.base_score = 100
        self.mult = 1.0

        from typing import Any
        self.current_minigame: Any = None
        
        self.msg = ""
        self.msg_timer = 0
        
        self.shake = ScreenShake()
        self.particles = ParticleSystem()
        self.texts = FloatingTextSystem()
        
        pyxel.mouse(True)

    def show_msg(self, text):
        self.msg = text
        self.msg_timer = 90

    def start_minigame(self, choice):
        if choice == 1:
            self.current_minigame = MiniGameZeroHour(self.round)
        elif choice == 2:
            self.current_minigame = MiniGameSignal(self.round)
        elif choice == 3:
            self.current_minigame = MiniGameGlitch(self.round)
        self.state = "PLAYING"

    def complete_minigame(self, won):
        self.state = "MENU"
        self.current_minigame = None
        if won:
            # Score calc
            earned = int(self.base_score * self.mult)
            self.chips += earned
            self.show_msg(f"成功! 获得 {earned} 理智片")
            self.particles.emit(128, 128, 30, [9, 10, 11], 3.0, 40)
            self.texts.emit(128, 100, f"+{earned} CHIPS", 11, 45)
            
            if self.chips >= self.target_chips:
                self.state = "SHOP"
                self.gold += 15 + self.round * 5
                self.show_msg("目标达成! 进入安全屋(商店)")
        else:
            self.hp -= 1
            self.show_msg("失败! 失去 1 肢体")
            self.shake.add_shake(8.0)
            self.particles.emit(128, 128, 20, [8, 2, 1], 2.0, 30)
            self.texts.emit(128, 100, "-1 HP", 8, 45)
            
            if self.hp <= 0:
                self.state = "GAMEOVER"

    def update(self) -> str:
        self.shake.update()
        self.particles.update()
        self.texts.update()
        
        if pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_Q):
            pyxel.mouse(False)
            return "QUIT_TO_MENU"

        if self.msg_timer > 0:
            self.msg_timer -= 1

        if self.state == "MENU":
            if pyxel.btnp(pyxel.KEY_1):
                self.start_minigame(1)
            elif pyxel.btnp(pyxel.KEY_2):
                self.start_minigame(2)
            elif pyxel.btnp(pyxel.KEY_3):
                self.start_minigame(3)

        elif self.state == "PLAYING":
            self.current_minigame.update()
            if self.current_minigame.result == "WIN":
                self.complete_minigame(True)
            elif self.current_minigame.result == "LOSE":
                self.complete_minigame(False)

        elif self.state == "SHOP":
            if pyxel.btnp(pyxel.KEY_X):
                # Flesh Factory mechanic
                if self.hp > 1:
                    self.max_hp -= 1
                    self.hp -= 1
                    self.gold += 50
                    self.show_msg("献祭肢体! 获得 $50")
                    self.shake.add_shake(10.0)
                    self.particles.emit(128, 128, 40, [8, 14, 2], 3.0, 30)
                    self.texts.emit(128, 100, "FLESH RIPPED! +$50", 8, 50)
            if pyxel.btnp(pyxel.KEY_B):
                if self.gold >= 20:
                    self.gold -= 20
                    self.mult += 0.5
                    self.show_msg("购买倍率罐头! 乘区 +0.5")
                    self.texts.emit(128, 120, "MULT UP!", 10, 40)
            if pyxel.btnp(pyxel.KEY_SPACE):
                # Next round
                self.round += 1
                self.chips = 0
                self.target_chips = int(self.target_chips * 1.5)
                self.state = "MENU"
                
        elif self.state == "GAMEOVER":
            if pyxel.btnp(pyxel.KEY_R):
                self.__init__(self.font)

        return "RUNNING"
        
    def draw_hud(self):
        # Draw dark top bar
        pyxel.rect(0, 0, 256, 30, 0)
        pyxel.line(0, 30, 256, 30, 5)
        
        if self.font:
            pyxel.text(5, 5, f"回合: {self.round}  目标: {self.chips}/{self.target_chips}", 7, self.font)
            pyxel.text(5, 15, f"金币: ${self.gold}  基础分: {self.base_score}  乘区: x{self.mult}", 10, self.font)
            pyxel.text(200, 5, f"HP: {self.hp}/{self.max_hp}", 8, self.font)
        else:
            pyxel.text(5, 5, f"Round: {self.round} Chips: {self.chips}/{self.target_chips}", 7)

        if self.msg_timer > 0:
            if self.font:
                pyxel.text(128 - len(self.msg)*4, 120, self.msg, 9, self.font)

    def draw_monitor_bezel(self):
        # Fake CRT vignette/bezel
        pyxel.rectb(2, 2, 252, 252, 1)
        pyxel.rectb(3, 3, 250, 250, 5)
        pyxel.rectb(4, 4, 248, 248, 1)

    def draw(self) -> None:
        ox, oy = self.shake.get_offset()
        # To draw shake globally in UI, we can just apply offset to everything, but Pyxel's camera is best
        pyxel.camera(-ox, -oy)
        
        if self.state == "MENU":
            pyxel.cls(1)
            self.draw_hud()
            
            # Decorate menu
            for i in range(0, 256, 16):
                pyxel.line(0, i, 256, i, 0) # scanlines

            if self.font:
                # shadow text
                pyxel.text(51, 61, "--- 惊悚赌局 ---", 1, self.font)
                pyxel.text(50, 60, "--- 惊悚赌局 ---", 8, self.font)
                
                # simple hover tweens for menu
                mx, my = pyxel.mouse_x, pyxel.mouse_y
                c1, c2, c3 = 7, 7, 7
                if point_in_rect(mx, my, 40, 100, 150, 10): c1 = 10
                if point_in_rect(mx, my, 40, 120, 150, 10): c2 = 10
                if point_in_rect(mx, my, 40, 140, 180, 10): c3 = 10
                
                pyxel.text(40, 100, "[1] 玩《零点循环》找茬", c1, self.font)
                pyxel.text(40, 120, "[2] 玩《深空信号》调频", c2, self.font)
                pyxel.text(40, 140, "[3] 玩《乱序终端》背密码", c3, self.font)
            else:
                pyxel.text(50, 60, "--- BALATRO OF MADNESS ---", 8)

        elif self.state == "PLAYING":
            self.current_minigame.draw(self.font, self.particles)
            # HUD overlay
            if self.font:
                pyxel.text(200, 5, f"HP: {self.hp}/{self.max_hp}", 8, self.font)

        elif self.state == "SHOP":
            pyxel.cls(2)
            for i in range(0, 256, 16):
                pyxel.line(0, i, 256, i, 1) # grid lines

            self.draw_hud()
            
            # Panels backing for shop items
            pyxel.rect(20, 80, 216, 50, 0)
            pyxel.rectb(20, 80, 216, 50, 5)
            
            if self.font:
                pyxel.text(80, 50, "--- 黑市交易 ---", 10, self.font)
                pyxel.text(30, 90, "[B] ${20} 购买 倍率强化 (乘区 +0.5)", 7, self.font)
                pyxel.text(30, 110, "[X] 免费 献祭肢体 (失去1上限, 得$50)", 8, self.font)
                
                pyxel.rect(20, 140, 216, 20, 1)
                pyxel.text(60, 146, "按 [SPACE] 进入下一回合", 13, self.font)

        elif self.state == "GAMEOVER":
            pyxel.cls(0)
            if self.font:
                pyxel.text(90, 100, "你 被 吞 噬 了", 8, self.font)
                pyxel.text(90, 120, "按 [R] 重新开始", 7, self.font)
                pyxel.text(90, 140, "按 [Q] 返回菜单", 13, self.font)

        # Global Juice Layer
        # Reset camera to draw particles/texts normally or with shake
        pyxel.camera(0, 0)
        self.particles.draw()
        self.texts.draw(self.font)
        
        # Reset camera
        pyxel.camera(0, 0)
        self.draw_monitor_bezel()
