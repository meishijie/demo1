from __future__ import annotations

import pyxel

from horror_engine.helpers import PLAYFIELD_HEIGHT, clamp, draw_meter, point_in_rect, rects_overlap
from horror_engine.manager import HorrorDemo


class ForestOfEyes(HorrorDemo):
    title_en = "Forest of Eyes"
    title_cn = "眼之森林"
    description_cn = "一位充满敌意的神明在松林上空注视。闭眼时移动，睁眼时躲避。"
    goal_cn = "穿越丛林，触碰圣地，同时保持侦测值在崩溃线以下。"
    controls_cn = "WASD: 移动"
    accent_color = 9

    def __init__(self, font: pyxel.Font | None = None):
        super().__init__(font=font)
        self.px = 22.0
        self.py = 184.0
        self.exit_rect = (212, 16, 18, 18)
        self.trees = [
            (34, 150, 24, 40),
            (86, 104, 24, 44),
            (136, 152, 26, 36),
            (180, 98, 24, 44),
            (200, 42, 22, 36),
        ]
        self.eye_state = 0
        self.eye_timer = 100
        self.detection = 0.0
        self.set_status("巨眼已闭合", "侦测值 0%")

    def is_hidden(self) -> bool:
        for tree in self.trees:
            if rects_overlap(self.px, self.py, 8, 8, *tree):
                return True
        return False

    def _advance_eye_cycle(self) -> None:
        self.eye_timer -= 1
        if self.eye_timer > 0:
            return
        if self.eye_state == 0:
            self.eye_state = 1
            self.eye_timer = 40
        elif self.eye_state == 1:
            self.eye_state = 2
            self.eye_timer = 70
        else:
            self.eye_state = 0
            self.eye_timer = 100

    def update(self) -> None:
        if pyxel.btn(pyxel.KEY_W):
            self.py -= 1.5
        if pyxel.btn(pyxel.KEY_S):
            self.py += 1.5
        if pyxel.btn(pyxel.KEY_A):
            self.px -= 1.5
        if pyxel.btn(pyxel.KEY_D):
            self.px += 1.5

        self.px = clamp(self.px, 6, 240)
        self.py = clamp(self.py, 12, PLAYFIELD_HEIGHT - 20)

        self._advance_eye_cycle()

        if self.eye_state == 2 and not self.is_hidden():
            self.detection += 2.4
        else:
            self.detection = max(0.0, self.detection - 3.5)

        if self.detection >= 100:
            self.mark_failure("巨眼记住了你的轮廓。森林将永远注视着你。")
        elif point_in_rect(self.px + 4, self.py + 4, self.exit_rect):
            self.mark_success("当巨眼在错误的阴影中搜索时，你潜入了神社。")

        state_name = ["已闭合", "正在睁开...", "已睁开！"][self.eye_state]
        self.set_status(f"巨眼：{state_name}", f"侦测进度 {int(self.detection)}%")

    def draw(self) -> None:
        pyxel.cls(3)
        pyxel.rect(0, 0, 256, PLAYFIELD_HEIGHT, 3)
        pyxel.rect(0, 0, 256, 48, 1)

        if self.eye_state > 0:
            pyxel.ellipse(128, 24, 86, 28, 7)
            pupil_color = 10 if self.eye_state == 1 else 8
            pyxel.circ(128, 24, 10, pupil_color)
            if self.eye_state == 2:
                pyxel.line(128, 24, 112, 10, 8)
                pyxel.line(128, 24, 142, 12, 8)
                pyxel.line(128, 24, 150, 32, 8)

        for tree in self.trees:
            pyxel.rect(tree[0], tree[1], tree[2], tree[3], 11 if self.eye_state == 0 else 3)
            pyxel.rectb(tree[0], tree[1], tree[2], tree[3], 1)

        pyxel.rect(self.exit_rect[0], self.exit_rect[1], self.exit_rect[2], self.exit_rect[3], 6)
        pyxel.rectb(self.exit_rect[0], self.exit_rect[1], self.exit_rect[2], self.exit_rect[3], 7)

        pyxel.rect(self.px, self.py, 8, 8, 11)
        if self.is_hidden():
            pyxel.text(self.px - 6, self.py - 8, "已隐藏", 7, self.font)
        elif self.eye_state == 2:
            pyxel.text(self.px - 6, self.py - 8, "跑！！", 8, self.font)

        draw_meter(150, 205, 80, self.detection, 100, 8)
