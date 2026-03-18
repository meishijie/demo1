from __future__ import annotations

import math
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
