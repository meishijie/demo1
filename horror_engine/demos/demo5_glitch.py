from __future__ import annotations

import random

import pyxel

from horror_engine.helpers import draw_panel, point_in_rect
from horror_engine.manager import HorrorDemo


class GlitchFloor13(HorrorDemo):
    title_en = "Glitch: Floor 13"
    title_cn = "故障：13层"
    description_cn = "电梯只接受某种仪式的重启。在损坏吞噬整个面板前，输入正确的序列。"
    goal_cn = "观察并记住随机的重启序列，在面板上依次尝试。每次故障面板都可能重新洗牌。"
    controls_cn = "鼠标: 点击控制面板"
    uses_mouse = True
    accent_color = 13

    def __init__(self, font: pyxel.Font | None = None):
        super().__init__(font=font)
        self.buttons = [
            [96, 64, 26, 24, "1"],
            [132, 64, 26, 24, "2"],
            [96, 98, 26, 24, "3"],
            [132, 98, 26, 24, "13"],
        ]
        self.sequence = [random.choice(["1", "2", "3", "13"]) for _ in range(5)]
        self.progress = 0
        self.corruption = 0
        self.preview_timer = 90
        self.display = f"序列: {' > '.join(self.sequence)}"
        self.glitch_frames = 0
        self.floor = "1"
        self.set_status("进度 0/5", "损坏值 0/3")

    def shuffle_buttons(self) -> None:
        positions = [(96, 64), (132, 64), (96, 98), (132, 98)]
        random.shuffle(positions)
        for i, b in enumerate(self.buttons):
            b[0], b[1] = positions[i][0], positions[i][1]

    def press_button(self, label: str) -> None:
        if self.finished or self.preview_timer > 0:
            return
        self.floor = label
        expected = self.sequence[self.progress]
        if label == expected:
            self.progress += 1
            self.glitch_frames = 18
            self.display = "重启准备就绪" if self.progress == len(self.sequence) else f"锁定 {self.progress}/{len(self.sequence)}"
            self.shuffle_buttons()
            if self.progress == len(self.sequence):
                self.mark_success("13层电梯门在错误中打开。电梯里似乎已经有了乘客。")
        else:
            self.progress = 0
            self.corruption += 1
            self.glitch_frames = 45
            self.display = "序列失步"
            self.shuffle_buttons()
            if self.corruption >= 3:
                self.mark_failure("面板先一步学习了你的模式。显示屏将永远无法显示层数。")

    def update(self) -> None:
        if self.preview_timer > 0:
            self.preview_timer -= 1
            if self.preview_timer == 0:
                self.display = "等待输入..."
                self.shuffle_buttons()
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            for button in self.buttons:
                if point_in_rect(pyxel.mouse_x, pyxel.mouse_y, button[:4]):
                    self.press_button(button[4])
                    break

        if self.glitch_frames > 0:
            self.glitch_frames -= 1

        self.set_status(f"进度 {self.progress}/{len(self.sequence)}", f"损坏值 {self.corruption}/3")

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

