from __future__ import annotations

import math
import random
import pyxel

from horror_engine.helpers import clamp, draw_meter
from horror_engine.manager import HorrorDemo


class SignalOfDespair(HorrorDemo):
    title_en = "Signal of Despair"
    title_cn = "绝望信号"
    description_cn = "在破旧收音机中寻找救援信号。小心！有些声音不该知道你的名字。"
    goal_cn = "在多维干扰中稳住波段。长按目标频率与天线角度锁定人类信号。"
    controls_cn = "左/右: 调频  上/下: 天线"
    accent_color = 10

    def __init__(self, font: pyxel.Font | None = None):
        super().__init__(font=font)
        self.frequency = 100.0
        self.antenna = 50.0
        self.target_frequency = 104.2
        self.target_antenna = 75.0
        self.false_frequency = 96.8
        self.false_antenna = 25.0
        self.signal_strength = 0.0
        self.lock_frames = 0
        self.false_lock = 0
        self.message = "扫描波段中..."
        self.temperature = "寂静"
        self.set_status("锁定 0/120", "波段寂静")

    def evaluate_signal(self) -> None:
        safe_diff = math.hypot(self.frequency - self.target_frequency, (self.antenna - self.target_antenna) * 0.2)
        false_diff = math.hypot(self.frequency - self.false_frequency, (self.antenna - self.false_antenna) * 0.2)
        self.signal_strength = max(0.0, 100 - safe_diff * 140)

        if safe_diff < 0.25:
            self.lock_frames += 1
        else:
            self.lock_frames = max(0, self.lock_frames - 2)

        if false_diff < 0.25:
            self.false_lock += 1
        else:
            self.false_lock = max(0, self.false_lock - 3)

        if self.lock_frames >= 120:
            self.mark_success("一个颤抖的声音传来：'千万不要回答另一个波段。'")
            return
        if self.false_lock >= 90:
            self.mark_failure("错误波段喊出了你的名字，房间里传来了回应。")
            return

        if safe_diff < 0.25:
            self.temperature = "锁定"
            self.message = "别动... 幸存者正在大门前等待..."
        elif safe_diff < 0.6:
            self.temperature = "温和"
            self.message = "快清晰了。保持双轴稳定。"
        elif false_diff < 0.35:
            self.temperature = "异常"
            self.message = "另一个声音：开门。开门。开门。"
        else:
            self.temperature = "寂静"
            self.message = "--- 杂音 ---"

    def update(self) -> None:
        if pyxel.btn(pyxel.KEY_LEFT):
            self.frequency -= 0.08
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.frequency += 0.08
        if pyxel.btn(pyxel.KEY_UP):
            self.antenna -= 0.6
        if pyxel.btn(pyxel.KEY_DOWN):
            self.antenna += 0.6

        if pyxel.frame_count % 4 == 0:
            self.frequency += random.uniform(-0.05, 0.05)
            self.antenna += random.uniform(-0.3, 0.3)

        self.frequency = clamp(self.frequency, 88.0, 108.0)
        self.antenna = clamp(self.antenna, 0.0, 100.0)
        self.evaluate_signal()
        self.set_status(f"锁定进度 {self.lock_frames}/120", f"波段：{self.temperature}")

    def draw(self) -> None:
        pyxel.cls(0)
        pyxel.rect(28, 40, 200, 136, 13)
        pyxel.rectb(28, 40, 200, 136, 5)
        pyxel.rect(44, 56, 144, 36, 0)
        pyxel.rect(52, 102, 128, 6, 5)

        dial_x = 52 + ((self.frequency - 88.0) / 20.0) * 128
        pyxel.line(dial_x, 102, dial_x, 108, 8 if self.temperature == "异常" else 10)
        pyxel.text(54, 65, f"频率: {self.frequency:05.2f}", 10)
        pyxel.text(54, 75, f"天线: {self.antenna:05.1f}", 10)

        pyxel.text(52, 110, "88.0", 7)
        pyxel.text(156, 110, "108.0", 7)

        pyxel.rect(52, 122, 128, 6, 5)
        dial_y = 52 + (self.antenna / 100.0) * 128
        pyxel.line(dial_y, 122, dial_y, 128, 8 if self.temperature == "异常" else 10)
        if self.font:
            pyxel.text(32, 122, "天线", 7, self.font)
        else:
            pyxel.text(32, 122, "ANT", 7)

        pyxel.rect(44, 134, 164, 28, 1)
        if self.font:
            pyxel.text(52, 144, self.message, 8 if self.temperature == "异常" else 7, self.font)
        else:
            pyxel.text(52, 144, self.message[:38], 8 if self.temperature == "异常" else 7)

        for dot in range(0, int((100 - self.signal_strength) / 2), 2):
            pyxel.pset(36 + (dot * 7) % 172, 18 + (dot * 11) % 180, 5)

        draw_meter(150, 199, 80, self.signal_strength, 100, 10)
        draw_meter(150, 205, 80, self.false_lock, 90, 8)
