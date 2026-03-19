from __future__ import annotations

import pyxel

from horror_engine.helpers import PLAYFIELD_HEIGHT, clamp, distance, draw_meter
from horror_engine.manager import HorrorDemo


class BloodMoonHunt(HorrorDemo):
    title_en = "Blood Moon Hunt"
    title_cn = "血月狩猎"
    description_cn = "你是村庄里的幽灵。熄灭火把，显露真身，将每一个目击者赶进深渊。小心巡逻的守卫。"
    goal_cn = "熄灭灯火，恐吓村民。如果被守卫的提灯照亮且你正在显形，幽灵就会消散。"
    controls_cn = "WASD: 飘动  空格: 熄灭火把"
    accent_color = 8

    def __init__(self, font: pyxel.Font | None = None):
        super().__init__(font=font)
        self.px = 36.0
        self.py = 116.0
        self.visibility = 0.0
        self.timer = 1800
        self.escaped = 0
        self.torches = [
            {"x": 78.0, "y": 70.0, "on": True},
            {"x": 132.0, "y": 118.0, "on": True},
            {"x": 92.0, "y": 166.0, "on": True},
            {"x": 178.0, "y": 96.0, "on": True},
        ]
        self.villagers = [
            {"x": 98.0, "y": 70.0, "fear": 0.0, "state": "calm"},
            {"x": 144.0, "y": 126.0, "fear": 0.0, "state": "calm"},
            {"x": 112.0, "y": 166.0, "fear": 0.0, "state": "calm"},
            {"x": 192.0, "y": 88.0, "fear": 0.0, "state": "calm"},
        ]
        self.guard = {"x": 128.0, "y": 140.0, "vx": 1.2, "vy": -0.7}
        self.set_status("已逃离 0/4", "火把 4")

    def extinguish_nearby_torches(self) -> None:
        for torch in self.torches:
            if torch["on"] and distance(self.px, self.py, torch["x"], torch["y"]) < 22:
                torch["on"] = False

    def _villager_in_light(self, villager: dict[str, float | str]) -> bool:
        for torch in self.torches:
            if torch["on"] and distance(float(villager["x"]), float(villager["y"]), torch["x"], torch["y"]) < 34:
                return True
        return False

    def update(self) -> None:
        dx = 0.0
        dy = 0.0
        if pyxel.btn(pyxel.KEY_W):
            dy -= 1.8
        if pyxel.btn(pyxel.KEY_S):
            dy += 1.8
        if pyxel.btn(pyxel.KEY_A):
            dx -= 1.8
        if pyxel.btn(pyxel.KEY_D):
            dx += 1.8

        self.px = clamp(self.px + dx, 10, 228)
        self.py = clamp(self.py + dy, 12, PLAYFIELD_HEIGHT - 16)

        moving = dx != 0 or dy != 0
        if moving:
            self.visibility = min(100.0, self.visibility + 5.5)
        else:
            self.visibility = max(0.0, self.visibility - 1.2)

        if pyxel.btnp(pyxel.KEY_SPACE):
            self.extinguish_nearby_torches()

        if not self.finished:
            self.timer = max(0, self.timer - 1)
            
            # Update guard
            self.guard["x"] = float(self.guard["x"]) + float(self.guard["vx"])
            self.guard["y"] = float(self.guard["y"]) + float(self.guard["vy"])
            
            if float(self.guard["x"]) < 20 or float(self.guard["x"]) > 220:
                self.guard["vx"] = -float(self.guard["vx"])
            if float(self.guard["y"]) < 20 or float(self.guard["y"]) > PLAYFIELD_HEIGHT - 20:
                self.guard["vy"] = -float(self.guard["vy"])
                
            if distance(self.px, self.py, float(self.guard["x"]), float(self.guard["y"])) < 40 and self.visibility > 12:
                self.mark_failure("守卫的提灯驱散了你。你成为了真正的虚无。")

        for villager in self.villagers:
            if villager["state"] == "escaped":
                continue

            if villager["state"] == "fleeing":
                villager["x"] = float(villager["x"]) + 1.8
                if float(villager["x"]) > 236:
                    villager["state"] = "escaped"
                    self.escaped += 1
                continue

            lit = self._villager_in_light(villager)
            close_to_ghost = distance(self.px, self.py, float(villager["x"]), float(villager["y"])) < 38
            if not lit and close_to_ghost and self.visibility > 24:
                villager["fear"] = min(40.0, float(villager["fear"]) + 4)
            else:
                villager["fear"] = max(0.0, float(villager["fear"]) - 1)

            if float(villager["fear"]) >= 28:
                villager["state"] = "fleeing"

        if self.escaped == len(self.villagers):
            self.mark_success("最后的目击者跳入了深渊。黎明照亮了一座空村。")
        elif self.timer == 0:
            self.mark_failure("黎明在恐慌蔓延前驱散了幽灵。")

        torches_lit = sum(1 for torch in self.torches if torch["on"])
        self.set_status(f"已驱逐村民 {self.escaped}/4", f"剩余火把 {torches_lit}")

    def draw(self) -> None:
        pyxel.cls(1)
        pyxel.rect(0, 0, 256, PLAYFIELD_HEIGHT, 1)
        pyxel.rect(222, 0, 34, PLAYFIELD_HEIGHT, 0)
        pyxel.rectb(220, 0, 36, PLAYFIELD_HEIGHT, 8)

        for torch in self.torches:
            if torch["on"]:
                pyxel.circ(torch["x"], torch["y"], 22, 10)
                pyxel.circ(torch["x"], torch["y"], 3, 7)
            else:
                pyxel.circ(torch["x"], torch["y"], 3, 13)

        gx = float(self.guard["x"])
        gy = float(self.guard["y"])
        pyxel.circ(gx, gy, 40, 9)
        pyxel.circ(gx, gy, 4, 8)
        pyxel.circ(gx, gy, 2, 10)

        for villager in self.villagers:
            if villager["state"] == "escaped":
                continue
            color = 11 if float(villager["fear"]) < 20 else 8
            pyxel.rect(villager["x"], villager["y"], 6, 6, color)
            if villager["state"] == "fleeing":
                pyxel.text(villager["x"] - 1, villager["y"] - 8, "!", 8)

        ghost_color = 7 if self.visibility > 55 else 6
        if self.visibility > 8:
            pyxel.circb(self.px, self.py, 5, ghost_color)
        else:
            pyxel.pset(self.px, self.py, 7)

        draw_meter(150, 199, 80, self.timer, 1800, 10)
        draw_meter(150, 205, 80, self.visibility, 100, 8)
