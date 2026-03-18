import pyxel
from horror_engine.manager import HorrorManager
from horror_engine.demos.demo1_abyssal import AbyssalEchoes
from horror_engine.demos.demo2_loop import ZeroHourLoop
from horror_engine.demos.demo3_flesh import FleshFactory
from horror_engine.demos.demo4_eyes import ForestOfEyes
from horror_engine.demos.demo5_glitch import GlitchFloor13
from horror_engine.demos.demo6_hunt import BloodMoonHunt
from horror_engine.demos.demo7_signal import SignalOfDespair

class App:
    def __init__(self):
        # 256x256 is a good standard for these demos
        pyxel.init(256, 256, title="Nightmare Collection - Micro Jam 055")
        
        # Load Chinese font
        self.font = None
        try:
            self.font = pyxel.Font("assets/font.bdf")
        except Exception:
            print("Warning: could not load fonts/font.bdf. Using default.")

        self.manager = HorrorManager([
            AbyssalEchoes,
            ZeroHourLoop,
            FleshFactory,
            ForestOfEyes,
            GlitchFloor13,
            BloodMoonHunt,
            SignalOfDespair
        ], font=self.font)
        
        pyxel.run(self.update, self.draw)

    def update(self):
        self.manager.update()

    def draw(self):
        self.manager.draw()

if __name__ == "__main__":
    App()
