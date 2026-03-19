from __future__ import annotations

import math
import random
from typing import Iterable

import pyxel

SCREEN_WIDTH = 256
SCREEN_HEIGHT = 256
PLAYFIELD_HEIGHT = 216
HUD_HEIGHT = SCREEN_HEIGHT - PLAYFIELD_HEIGHT


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def distance(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(bx - ax, by - ay)


def point_in_rect(x: float, y: float, rect: tuple[float, float, float, float]) -> bool:
    rx, ry, rw, rh = rect
    return rx <= x <= rx + rw and ry <= y <= ry + rh


def rects_overlap(
    ax: float,
    ay: float,
    aw: float,
    ah: float,
    bx: float,
    by: float,
    bw: float,
    bh: float,
) -> bool:
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def draw_centered_text(y: int, text: str, color: int, font: pyxel.Font | None = None) -> None:
    x = max(0, (SCREEN_WIDTH - len(text) * (8 if font else 4)) // 2)
    pyxel.text(x, y, text, color, font)


def draw_panel(x: int, y: int, w: int, h: int, fill: int, border: int) -> None:
    pyxel.rect(x, y, w, h, fill)
    pyxel.rectb(x, y, w, h, border)


def wrap_text(text: str, width_chars: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_wrapped_text(
    x: int,
    y: int,
    text: str,
    color: int,
    width_chars: int,
    line_height: int = 10,
    font: pyxel.Font | None = None,
) -> int:
    lines = wrap_text(text, width_chars)
    for index, line in enumerate(lines):
        pyxel.text(x, y + index * line_height, line, color, font)
    return y + len(lines) * line_height


def draw_meter(x: int, y: int, width: int, value: float, maximum: float, color: int) -> None:
    pyxel.rect(x, y, width, 4, 1)
    if maximum <= 0:
        return
    fill = int(width * clamp(value / maximum, 0, 1))
    if fill > 0:
        pyxel.rect(x, y, fill, 4, color)
    pyxel.rectb(x, y, width, 4, 5)


def draw_hud(
    title: str,
    goal: str,
    controls: str,
    status_lines: Iterable[str],
    accent: int,
    font: pyxel.Font | None = None,
) -> None:
    draw_panel(0, PLAYFIELD_HEIGHT, SCREEN_WIDTH, HUD_HEIGHT, 0, accent)
    pyxel.text(6, PLAYFIELD_HEIGHT + 4, title, accent, font)
    draw_wrapped_text(6, PLAYFIELD_HEIGHT + 13, goal, 7, 30, font=font)
    pyxel.text(6, PLAYFIELD_HEIGHT + 28, controls, 6, font)

    right_y = PLAYFIELD_HEIGHT + 4
    for line in status_lines:
        pyxel.text(160, right_y, line, 7, font)
        right_y += 10


def draw_outcome_overlay(title: str, message: str, success: bool, font: pyxel.Font | None = None) -> None:
    accent = 11 if success else 8
    draw_panel(34, 72, 188, 72, 0, accent)
    draw_centered_text(84, title, accent, font=font)
    draw_wrapped_text(48, 98, message, 7, 24, font=font)
    draw_centered_text(126, "R: 重试 (Restart)  ESC: 返回菜单 (Menu)", 6, font=font)

# --- JUICE SYSTEMS ---

class Particle:
    def __init__(self, x: float, y: float, vx: float, vy: float, life: int, color: int):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.9  # friction
        self.vy *= 0.9
        self.life -= 1

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x: float, y: float, count: int, color_list: list[int], speed: float = 2.0, life: int = 20):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            s = random.uniform(speed * 0.2, speed)
            c = random.choice(color_list)
            l = random.randint(life // 2, life)
            self.particles.append(Particle(x, y, math.cos(angle) * s, math.sin(angle) * s, l, c))

    def update(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]

    def draw(self, cam_x: float = 0, cam_y: float = 0):
        for p in self.particles:
            if pyxel.frame_count % 3 != 0 or p.life > p.max_life // 3:
                pyxel.pset(p.x - cam_x, p.y - cam_y, p.color)

class FloatingText:
    def __init__(self, x: float, y: float, text: str, color: int, life: int = 45):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = life
        self.max_life = life

    def update(self):
        self.y -= 0.5 # Float upwards
        self.life -= 1

class FloatingTextSystem:
    def __init__(self):
        self.texts = []

    def emit(self, x: float, y: float, text: str, color: int, life: int = 45):
        self.texts.append(FloatingText(x, y + random.randint(-5, 5), text, color, life))

    def update(self):
        for t in self.texts:
            t.update()
        self.texts = [t for t in self.texts if t.life > 0]

    def draw(self, font: pyxel.Font | None, cam_x: float = 0, cam_y: float = 0):
        for t in self.texts:
            if t.life < 10 and pyxel.frame_count % 2 == 0:
                continue # flicker before vanishing
            if font:
                pyxel.text(t.x - cam_x, t.y - cam_y, t.text, t.color, font)
            else:
                pyxel.text(t.x - cam_x, t.y - cam_y, t.text, t.color)

class ScreenShake:
    def __init__(self):
        self.intensity = 0.0
        self.decay = 0.9

    def add_shake(self, amount: float):
        self.intensity = min(self.intensity + amount, 20.0)

    def update(self):
        if self.intensity > 0.1:
            self.intensity *= self.decay
        else:
            self.intensity = 0.0

    def get_offset(self) -> tuple[float, float]:
        if self.intensity <= 0:
            return 0.0, 0.0
        # return random offset based on intensity
        ox = random.uniform(-self.intensity, self.intensity)
        oy = random.uniform(-self.intensity, self.intensity)
        return ox, oy
