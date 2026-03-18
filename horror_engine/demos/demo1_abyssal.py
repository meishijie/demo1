from __future__ import annotations

import math

import pyxel

from horror_engine.helpers import (
    PLAYFIELD_HEIGHT,
    clamp,
    distance,
    draw_meter,
    point_in_rect,
    rects_overlap,
)
from horror_engine.manager import HorrorDemo


class AbyssalEchoes(HorrorDemo):
    title_en = "Abyssal Echoes"
    title_cn = "深渊回声"
    description_cn = "在溺水的地下迷宫通过声呐导航。每次砰砰声都会描绘路径，但也唤醒了下方的猎手。"
    goal_cn = "在怪物追上你之前，到达右上角的舱口。"
    controls_cn = "WASD: 移动  空格: 声呐脉冲"
    accent_color = 12

    def __init__(self, font: pyxel.Font | None = None):
        super().__init__(font=font)
        self.player_x = 24.0
        self.player_y = 188.0
        self.player_size = 8
        self.speed = 1.6
        self.exit_rect = (224, 20, 18, 18)
        self.pulses: list[list[float]] = []
        self.ping_count = 0
        self.revealed_exit_timer = 0
        self.revealed_walls: dict[int, int] = {}
        self.walls = [
            (64, 24, 10, 140),
            (64, 164, 88, 10),
            (144, 60, 10, 114),
            (144, 60, 70, 10),
            (206, 60, 10, 120),
        ]
        self.enemy_x = 220.0
        self.enemy_y = 184.0
        self.enemy_awake = False
        self.enemy_speed = 0.45
        self.set_status("脉冲 0", "威胁：沉睡中")

    def emit_pulse(self) -> None:
        if self.finished:
            return
        self.pulses.append([self.player_x + 4, self.player_y + 4, 0, 110])
        self.ping_count += 1
        self.revealed_exit_timer = 42
        self.enemy_awake = True

    def _can_move_to(self, new_x: float, new_y: float) -> bool:
        if new_x < 8 or new_y < 8 or new_x + self.player_size > 248 or new_y + self.player_size > PLAYFIELD_HEIGHT - 6:
            return False
        for wall in self.walls:
            if rects_overlap(new_x, new_y, self.player_size, self.player_size, *wall):
                return False
        return True

    def _wave_hits_rect(
        self, pulse_x: float, pulse_y: float, radius: float, rect: tuple[float, float, float, float]
    ) -> bool:
        rx, ry, rw, rh = rect
        for corner_x, corner_y in (
            (rx, ry),
            (rx + rw, ry),
            (rx, ry + rh),
            (rx + rw, ry + rh),
        ):
            if abs(distance(pulse_x, pulse_y, corner_x, corner_y) - radius) < 6:
                return True
        return False

    def _check_outcome(self) -> None:
        if self.finished:
            return
        if point_in_rect(self.player_x + 4, self.player_y + 4, self.exit_rect):
            self.mark_success("你推开了舱门。远处的嘶吼声渐行渐远。")
            return
        if distance(self.player_x + 4, self.player_y + 4, self.enemy_x, self.enemy_y) < 9:
            self.mark_failure("回声给出了死亡的答复。下次请保持安静。")

    def update(self) -> None:
        move_x = 0.0
        move_y = 0.0
        if pyxel.btn(pyxel.KEY_W):
            move_y -= self.speed
        if pyxel.btn(pyxel.KEY_S):
            move_y += self.speed
        if pyxel.btn(pyxel.KEY_A):
            move_x -= self.speed
        if pyxel.btn(pyxel.KEY_D):
            move_x += self.speed

        if move_x and self._can_move_to(self.player_x + move_x, self.player_y):
            self.player_x += move_x
        if move_y and self._can_move_to(self.player_x, self.player_y + move_y):
            self.player_y += move_y

        if pyxel.btnp(pyxel.KEY_SPACE):
            self.emit_pulse()

        for pulse in self.pulses[:]:
            pulse[2] += 4
            if pulse[2] > pulse[3]:
                self.pulses.remove(pulse)
                continue
            for index, wall in enumerate(self.walls):
                if self._wave_hits_rect(pulse[0], pulse[1], pulse[2], wall):
                    self.revealed_walls[index] = 26
            if self._wave_hits_rect(pulse[0], pulse[1], pulse[2], self.exit_rect):
                self.revealed_exit_timer = 42

        for index in list(self.revealed_walls):
            self.revealed_walls[index] -= 1
            if self.revealed_walls[index] <= 0:
                del self.revealed_walls[index]

        if self.revealed_exit_timer > 0:
            self.revealed_exit_timer -= 1

        if self.enemy_awake:
            self.enemy_speed = 0.45 + min(0.55, self.ping_count * 0.08)
            dx = self.player_x + 4 - self.enemy_x
            dy = self.player_y + 4 - self.enemy_y
            gap = math.hypot(dx, dy)
            if gap > 0:
                self.enemy_x += dx / gap * self.enemy_speed
                self.enemy_y += dy / gap * self.enemy_speed

        self._check_outcome()
        threat = "正在猎杀！" if self.enemy_awake else "沉睡中"
        self.set_status(f"脉冲次数 {self.ping_count}", f"威胁：{threat}")

    def draw(self) -> None:
        pyxel.cls(0)

        for star_x in range(12, 244, 28):
            pyxel.pset(star_x, 12 + (star_x // 4 + pyxel.frame_count) % 18, 1)

        exit_color = 10 if self.revealed_exit_timer > 0 or self.finished else 1
        pyxel.rect(self.exit_rect[0], self.exit_rect[1], self.exit_rect[2], self.exit_rect[3], 1)
        pyxel.rectb(self.exit_rect[0], self.exit_rect[1], self.exit_rect[2], self.exit_rect[3], exit_color)

        for pulse_x, pulse_y, radius, max_radius in self.pulses:
            shade = 6 if radius < max_radius * 0.65 else 5
            pyxel.circb(pulse_x, pulse_y, radius, shade)

        for index, wall in enumerate(self.walls):
            color = 5 if index in self.revealed_walls else 1
            pyxel.rect(wall[0], wall[1], wall[2], wall[3], 0)
            pyxel.rectb(wall[0], wall[1], wall[2], wall[3], color)

        pyxel.rect(self.player_x, self.player_y, self.player_size, self.player_size, 7)

        if self.enemy_awake or self.finished:
            blink = 8 if (pyxel.frame_count // 8) % 2 == 0 else 2
            pyxel.circ(self.enemy_x, self.enemy_y, 4, blink)

        draw_meter(150, 205, 80, self.enemy_speed - 0.45, 0.55, 8)
