from __future__ import annotations

import random

import pyxel

from horror_engine.helpers import draw_panel, point_in_rect
from horror_engine.manager import HorrorDemo


class GlitchFloor13(HorrorDemo):
    title_en = "Glitch: Floor 13"
    title_cn = "故障：13层"
    description_cn = "电梯只接受某种仪式的重启。在损坏吞噬整个面板前，输入正确的序列。"
    goal_cn = "点击 1 -> 3 -> 2 -> 13。错过三次，电梯将把你永远关入舱室。"
    controls_cn = "鼠标: 点击控制面板"
    uses_mouse = True
    accent_color = 13

    def __init__(self, font: pyxel.Font | None = None):
        super().__init__(font=font)
        self.buttons = [
            (96, 64, 26, 24, "1"),
            (132, 64, 26, 24, "2"),
            (96, 98, 26, 24, "3"),
            (132, 98, 26, 24, "13"),
        ]
        self.sequence = ["1", "3", "2", "13"]
        self.progress = 0
        self.corruption = 0
        self.display = "补丁: 1 > 3 > 2 > 13"
        self.glitch_frames = 0
        self.floor = "1"
        self.set_status("进度 0/4", "损坏值 0/3")

    def press_button(self, label: str) -> None:
        if self.finished:
            return
        self.floor = label
        expected = self.sequence[self.progress]
        if label == expected:
            self.progress += 1
            self.glitch_frames = 18
            self.display = "重启准备就绪" if self.progress == 3 else f"步骤 {self.progress}/4 已锁定"
            if self.progress == len(self.sequence):
                self.mark_success("13层电梯门在错误中打开。电梯里似乎已经有了乘客。")
        else:
            self.progress = 0
            self.corruption += 1
            self.glitch_frames = 45
            self.display = "序列失步"
            if self.corruption >= 3:
                self.mark_failure("面板先一步学习了你的模式。显示屏将永远无法显示层数。")

    def update(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            for button in self.buttons:
                if point_in_rect(pyxel.mouse_x, pyxel.mouse_y, button[:4]):
                    self.press_button(button[4])
                    break

        if self.glitch_frames > 0:
            self.glitch_frames -= 1

        self.set_status(f"进度 {self.progress}/4", f"损坏值 {self.corruption}/3")

    def draw(self) -> None:
        pyxel.cls(1)
        pyxel.rect(74, 22, 108, 170, 5)
        pyxel.rectb(74, 22, 108, 170, 13)
        draw_panel(90, 34, 76, 22, 0, 7)
        pyxel.text(98, 42, self.floor if self.progress < 4 else "13", 8 if self.glitch_frames else 10)
        if self.font:
            pyxel.text(12, 58, self.display, 7 if self.corruption < 2 else 8, self.font)
        else:
            pyxel.text(24, 58, self.display, 7 if self.corruption < 2 else 8)

        if self.glitch_frames:
            for row in range(0, 170, 18):
                band_color = random.choice([2, 8, 13])
                pyxel.rect(80 + (row % 3) * 2, 26 + row, 96, 4, band_color)

        for bx, by, bw, bh, label in self.buttons:
            is_target = self.progress < len(self.sequence) and label == self.sequence[self.progress]
            fill = 7 if not is_target else 10
            pyxel.rect(bx, by, bw, bh, fill)
            pyxel.rectb(bx, by, bw, bh, 0 if is_target else 13)
            text_x = bx + 9 if len(label) == 1 else bx + 6
            pyxel.text(text_x, by + 9, label, 0)

