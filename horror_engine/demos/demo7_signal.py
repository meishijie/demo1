from __future__ import annotations

import pyxel

from horror_engine.helpers import clamp, draw_meter
from horror_engine.manager import HorrorDemo


class SignalOfDespair(HorrorDemo):
    title_en = "Signal of Despair"
    title_cn = "绝望信号"
    description_cn = "在破旧收音机中寻找救援信号。小心！有些声音不该知道你的名字。"
    goal_cn = "长按 104.2 MHz 锁定人类信号。徘徊在 96.8 MHz 附近将导致自我迷失。"
    controls_cn = "左/右: 调频"
    accent_color = 10

    def __init__(self, font: pyxel.Font | None = None):
        super().__init__(font=font)
        self.frequency = 100.0
        self.target_frequency = 104.2
        self.false_frequency = 96.8
        self.signal_strength = 0.0
        self.lock_frames = 0
        self.false_lock = 0
        self.message = "扫描波段中..."
        self.temperature = "寂静"
        self.set_status("锁定 0/120", "波段寂静")

    def evaluate_signal(self) -> None:
        safe_diff = abs(self.frequency - self.target_frequency)
        false_diff = abs(self.frequency - self.false_frequency)
        self.signal_strength = max(0.0, 100 - safe_diff * 220)

        if safe_diff < 0.12:
            self.lock_frames += 1
        else:
            self.lock_frames = max(0, self.lock_frames - 2)

        if false_diff < 0.12:
            self.false_lock += 1
        else:
            self.false_lock = max(0, self.false_lock - 3)

        if self.lock_frames >= 120:
            self.mark_success("一个颤抖的声音传来：'千万不要回答另一个波段。'")
            return
        if self.false_lock >= 90:
            self.mark_failure("错误波段喊出了你的名字，房间里传来了回应。")
            return

        if safe_diff < 0.12:
            self.temperature = "锁定"
            self.message = "别动... 幸存者正在大门前等待..."
        elif safe_diff < 0.35:
            self.temperature = "温和"
            self.message = "快清晰了。保持指针稳定。"
        elif false_diff < 0.22:
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

        self.frequency = clamp(self.frequency, 88.0, 108.0)
        self.evaluate_signal()
        self.set_status(f"锁定进度 {self.lock_frames}/120", f"波段：{self.temperature}")

    def draw(self) -> None:
        pyxel.cls(0)
        pyxel.rect(28, 40, 200, 136, 13)
        pyxel.rectb(28, 40, 200, 136, 5)
        pyxel.rect(44, 56, 144, 36, 0)
        pyxel.rect(52, 108, 128, 8, 5)

        dial_x = 52 + ((self.frequency - 88.0) / 20.0) * 128
        pyxel.line(dial_x, 108, dial_x, 116, 8 if self.temperature == "异常" else 10)
        pyxel.text(54, 65, f"{self.frequency:05.2f} MHz", 10)
        pyxel.text(52, 120, "88.0", 7)
        pyxel.text(156, 120, "108.0", 7)

        pyxel.rect(44, 134, 164, 28, 1)
        if self.font:
            pyxel.text(52, 144, self.message, 8 if self.temperature == "异常" else 7, self.font)
        else:
            pyxel.text(52, 144, self.message[:38], 8 if self.temperature == "异常" else 7)

        for dot in range(0, int((100 - self.signal_strength) / 2), 2):
            pyxel.pset(36 + (dot * 7) % 172, 18 + (dot * 11) % 180, 5)

        draw_meter(150, 199, 80, self.signal_strength, 100, 10)
        draw_meter(150, 205, 80, self.false_lock, 90, 8)
