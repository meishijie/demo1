from __future__ import annotations

import pyxel

from horror_engine.helpers import PLAYFIELD_HEIGHT, clamp, draw_meter, rects_overlap
from horror_engine.manager import HorrorDemo


class FleshFactory(HorrorDemo):
    title_en = "The Flesh Factory"
    title_cn = "血肉工厂"
    description_cn = "一座屠宰平台竖井提供了一个交易：献祭你的腿以跳得更高，逃离下方的研磨机。"
    goal_cn = "献祭双腿，攀爬血肉脚手架，在身体崩溃前进入升降机。"
    controls_cn = "A/D: 移动  W: 跳跃  X: 献祭"
    accent_color = 8

    def __init__(self, font: pyxel.Font | None = None):
        super().__init__(font=font)
        self.start_x = 24.0
        self.start_y = 184.0
        self.px = self.start_x
        self.py = self.start_y
        self.pvx = 0.0
        self.pvy = 0.0
        self.on_ground = False
        self.integrity = 100
        self.leg_sacrificed = False
        self.gravity = 0.38
        self.base_jump = -6.4
        self.platforms = [
            (0, 200, 256, 16),
            (48, 168, 56, 8),
            (118, 140, 44, 8),
            (168, 108, 34, 8),
            (196, 78, 42, 8),
        ]
        self.exit_rect = (208, 48, 22, 24)
        self.set_status("完整度 100%", "肢体完整")

    def sacrifice_leg(self) -> None:
        if self.leg_sacrificed or self.finished:
            return
        self.leg_sacrificed = True
        self.integrity -= 30
        if self.integrity <= 0:
            self.mark_failure("机器夺走了太多。剩下的部分已经无法爬出了。")

    def _reset_after_fall(self) -> None:
        self.px = self.start_x
        self.py = self.start_y
        self.pvx = 0
        self.pvy = 0
        self.integrity -= 15
        if self.integrity <= 0:
            self.mark_failure("传送带不断吞噬着碎片，直到不再剩下任何人类的意志。")

    def update(self) -> None:
        speed = 2.4 if not self.leg_sacrificed else 1.5
        if pyxel.btn(pyxel.KEY_A):
            self.pvx = -speed
        elif pyxel.btn(pyxel.KEY_D):
            self.pvx = speed
        else:
            self.pvx = 0

        if pyxel.btnp(pyxel.KEY_X):
            self.sacrifice_leg()

        if pyxel.btnp(pyxel.KEY_W) and self.on_ground:
            jump_boost = 1.35 if self.leg_sacrificed else 1.0
            self.pvy = self.base_jump * jump_boost
            self.on_ground = False

        self.pvy += self.gravity
        self.px = clamp(self.px + self.pvx, 0, 248)
        self.py += self.pvy

        self.on_ground = False
        for platform in self.platforms:
            px, py, pw, ph = platform
            if self.pvy >= 0 and rects_overlap(self.px, self.py, 8, 8, px, py, pw, ph):
                if self.py + 8 - self.pvy <= py + 2:
                    self.py = py - 8
                    self.pvy = 0
                    self.on_ground = True

        if self.py > PLAYFIELD_HEIGHT:
            self._reset_after_fall()

        if rects_overlap(self.px, self.py, 8, 8, *self.exit_rect):
            self.mark_success("升降机接受了报酬。大门在钩锁触及前关上了。")

        leg_state = "已献祭断肢" if self.leg_sacrificed else "肢体完整"
        self.set_status(f"身体完整度 {self.integrity}%", leg_state)

    def draw(self) -> None:
        pyxel.cls(0)

        for px, py, pw, ph in self.platforms:
            pyxel.rect(px, py, pw, ph, 14 if (pyxel.frame_count // 12) % 2 == 0 else 2)
            for offset in range(0, pw, 8):
                pyxel.line(px + offset, py, px + offset + 2, py + ph, 8)

        pyxel.rect(self.exit_rect[0], self.exit_rect[1], self.exit_rect[2], self.exit_rect[3], 1)
        pyxel.rectb(self.exit_rect[0], self.exit_rect[1], self.exit_rect[2], self.exit_rect[3], 10)
        pyxel.text(self.exit_rect[0] + 4, self.exit_rect[1] + 8, "升降机", 7, self.font)

        body_color = 8 if self.leg_sacrificed else 11
        pyxel.rect(self.px, self.py, 8, 8, body_color)
        if self.leg_sacrificed:
            pyxel.rect(self.px + 2, self.py + 6, 4, 2, 0)

        draw_meter(150, 205, 80, self.integrity, 100, 8)
