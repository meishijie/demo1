import pyxel
from horror_engine.mode_a_survivor import ModeASurvivor
from horror_engine.mode_b_gambler import ModeBGambler

class DualLauncher:
    def __init__(self):
        # 256x256 is the standard from previous
        pyxel.init(256, 256, title="Nightmare Origins: Dual Escape")
        
        self.font = None
        try:
            self.font = pyxel.Font("assets/font.bdf")
        except Exception:
            print("Warning: could not load fonts/font.bdf. Using default.")

        self.state = "MENU" # MENU, MODE_A, MODE_B
        self.mode_app = None

        pyxel.run(self.update, self.draw)

    def update(self):
        if self.state == "MENU":
            if pyxel.btnp(pyxel.KEY_1):
                self.mode_app = ModeASurvivor(self.font)
                self.state = "MODE_A"
            elif pyxel.btnp(pyxel.KEY_2):
                self.mode_app = ModeBGambler(self.font)
                self.state = "MODE_B"
        else:
            if self.mode_app:
                # Update returns "QUIT_TO_MENU" if it wants to go back
                result = self.mode_app.update()
                if result == "QUIT_TO_MENU":
                    self.state = "MENU"
                    self.mode_app = None

    def draw(self):
        if self.state == "MENU":
            pyxel.cls(0)
            
            title = "噩梦起源：双面逃生"
            title2 = "Nightmare Origins: Dual Escape"
            
            if self.font:
                pyxel.text(70, 40, title, 8, self.font)
                pyxel.text(50, 60, title2, 7)
                
                pyxel.text(40, 100, "按 [1] 进入 模式 A: 恐怖割草", 7, self.font)
                pyxel.text(40, 120, "(融合深渊、森林、血月)", 13, self.font)
                
                pyxel.text(40, 160, "按 [2] 进入 模式 B: 狂乱赌桌", 7, self.font)
                pyxel.text(40, 180, "(融合找茬、密码、调频与血肉献祭)", 13, self.font)
            else:
                pyxel.text(50, 40, "Nightmare Origins: Dual Escape", 8)
                pyxel.text(40, 100, "Press [1] -> Mode A: Horror Survivor", 7)
                pyxel.text(40, 160, "Press [2] -> Mode B: Balatro of Madness", 7)
        else:
            if self.mode_app:
                self.mode_app.draw()

if __name__ == "__main__":
    DualLauncher()
