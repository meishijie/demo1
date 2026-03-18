from __future__ import annotations

import pyxel

from horror_engine.helpers import PLAYFIELD_HEIGHT, clamp, distance, draw_panel, point_in_rect
from horror_engine.manager import HorrorDemo


class ZeroHourLoop(HorrorDemo):
    title_en = "Zero Hour Loop"
    title_cn = "零点循环"
    description_cn = "狭窄的公寓不断重置。观察每一处变化并揭穿它，走廊才会最终放过你。"
    goal_cn = "检查全部三个异常，在第六次循环前穿过顶部的门。"
    controls_cn = "WASD: 移动  E: 检查"
    accent_color = 10

    def __init__(self, font: pyxel.Font | None = None):
        super().__init__(font=font)
        self.room_rect = (48, 28, 160, 164)
        self.top_door = (112, 24, 32, 12)
        self.player_x = 124.0
        self.player_y = 174.0
        self.loops = 0
        self.inspected: set[str] = set()
        self.hint = "穿过顶部的门开始循环。"
        self.anomalies = [
            {"id": "painting", "rect": (72, 58, 20, 20), "loop": 1, "label": "画中的眼睛睁开了。"},
            {"id": "clock", "rect": (174, 54, 18, 18), "loop": 2, "label": "时钟正在倒着走。"},
            {"id": "mirror", "rect": (120, 104, 26, 38), "loop": 3, "label": "镜子里流出了杂色。"},
        ]
        self.set_status("循环 0/6", "异常 0/3")

    def _active_anomalies(self) -> list[dict[str, object]]:
        return [anomaly for anomaly in self.anomalies if self.loops >= anomaly["loop"]]

    def _door_should_break(self) -> bool:
        return self.loops >= 3 and len(self.inspected) == len(self.anomalies)

    def inspect_nearby_anomaly(self) -> bool:
        player_center = (self.player_x + 4, self.player_y + 4)
        for anomaly in self._active_anomalies():
            ax, ay, aw, ah = anomaly["rect"]
            if distance(player_center[0], player_center[1], ax + aw / 2, ay + ah / 2) < 20:
                self.inspected.add(str(anomaly["id"]))
                self.hint = str(anomaly["label"])
                return True
        self.hint = "这里没什么。记忆需要更敏锐一些。"
        return False

    def trigger_top_door(self) -> None:
        if self._door_should_break():
            self.mark_success("你认出了每一个谎言。第四条走廊通向了外界。")
            return

        self.loops += 1
        self.player_x = 124.0
        self.player_y = 174.0
        self.hint = f"第 {self.loops} 次循环：某些细节改变了。"
        if self.loops >= 6:
            self.mark_failure("你停止了寻找差异。公寓记住了你的名字。")

    def update(self) -> None:
        if pyxel.btn(pyxel.KEY_W):
            self.player_y -= 1.6
        if pyxel.btn(pyxel.KEY_S):
            self.player_y += 1.6
        if pyxel.btn(pyxel.KEY_A):
            self.player_x -= 1.6
        if pyxel.btn(pyxel.KEY_D):
            self.player_x += 1.6

        self.player_x = clamp(self.player_x, self.room_rect[0] + 4, self.room_rect[0] + self.room_rect[2] - 12)
        self.player_y = clamp(self.player_y, self.room_rect[1] + 4, PLAYFIELD_HEIGHT - 22)

        if pyxel.btnp(pyxel.KEY_E):
            self.inspect_nearby_anomaly()

        if point_in_rect(self.player_x + 4, self.player_y + 4, self.top_door):
            self.trigger_top_door()

        self.set_status(f"循环 {self.loops}/6", f"异常 {len(self.inspected)}/3")

    def draw(self) -> None:
        pyxel.cls(0)
        pyxel.rect(self.room_rect[0], self.room_rect[1], self.room_rect[2], self.room_rect[3], 5)
        pyxel.rectb(self.room_rect[0], self.room_rect[1], self.room_rect[2], self.room_rect[3], 1)

        door_color = 11 if self._door_should_break() else 12
        pyxel.rect(self.top_door[0], self.top_door[1], self.top_door[2], self.top_door[3], door_color)
        pyxel.rect(112, 188, 32, 8, 12)

        draw_panel(68, 54, 28, 28, 4, 7)
        if self.loops >= 1:
            eye_color = 8 if "painting" not in self.inspected else 10
            pyxel.circ(82, 68, 4, eye_color)
            pyxel.pset(82, 68, 0)

        draw_panel(170, 52, 24, 24, 1, 7)
        if self.loops >= 2:
            hand_color = 8 if (pyxel.frame_count // 10) % 2 == 0 else 7
            pyxel.line(182, 64, 176, 58, hand_color)
            pyxel.line(182, 64, 188, 70, hand_color)

        draw_panel(118, 100, 30, 44, 1, 7)
        if self.loops >= 3:
            bleed = 8 if "mirror" not in self.inspected else 10
            for offset in range(0, 24, 5):
                pyxel.line(122 + offset, 140, 120 + offset, 152, bleed)

        pyxel.rect(self.player_x, self.player_y, 8, 8, 11)
        if self.font:
            pyxel.text(10, 10, self.hint, 7, self.font)
        else:
            pyxel.text(10, 10, self.hint, 7)
