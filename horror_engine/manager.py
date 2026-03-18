from __future__ import annotations

from dataclasses import dataclass

import pyxel

from horror_engine.helpers import (
    PLAYFIELD_HEIGHT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    draw_centered_text,
    draw_hud,
    draw_outcome_overlay,
    draw_panel,
    draw_wrapped_text,
    point_in_rect,
)


@dataclass(frozen=True)
class DemoCatalogEntry:
    index: int
    demo_cls: type["HorrorDemo"]
    title_en: str
    title_cn: str
    description_cn: str
    goal_cn: str
    controls_cn: str
    uses_mouse: bool
    accent_color: int


class HorrorDemo:
    title_en = "Abstract Demo"
    title_cn = "抽象演示"
    description_cn = "基类描述"
    goal_cn = "在遭遇中存活。"
    controls_cn = "WASD: 移动"
    uses_mouse = False
    accent_color = 7

    def __init__(self, font: pyxel.Font | None = None):
        self.font = font
        self.outcome: str | None = None
        self.outcome_message = ""
        self.status_lines: list[str] = []

    @classmethod
    def catalog_entry(cls, index: int) -> DemoCatalogEntry:
        return DemoCatalogEntry(
            index=index,
            demo_cls=cls,
            title_en=cls.title_en,
            title_cn=cls.title_cn,
            description_cn=cls.description_cn,
            goal_cn=cls.goal_cn,
            controls_cn=cls.controls_cn,
            uses_mouse=cls.uses_mouse,
            accent_color=cls.accent_color,
        )

    @property
    def finished(self) -> bool:
        return self.outcome is not None

    def set_status(self, *lines: str) -> None:
        self.status_lines = [line for line in lines if line]

    def mark_success(self, message: str) -> None:
        self.outcome = "success"
        self.outcome_message = message

    def mark_failure(self, message: str) -> None:
        self.outcome = "failure"
        self.outcome_message = message

    def update(self) -> None:
        raise NotImplementedError

    def draw(self) -> None:
        raise NotImplementedError

    def draw_hud(self) -> None:
        draw_hud(self.title_cn, self.goal_cn, self.controls_cn, self.status_lines, self.accent_color, font=self.font)

    def draw_outcome_overlay(self) -> None:
        if not self.finished:
            return
        title = "成功逃脱 (ESCAPED)" if self.outcome == "success" else "遭遇杀害 (CLAIMED)"
        draw_outcome_overlay(title, self.outcome_message, self.outcome == "success", font=self.font)


class HorrorManager:
    def __init__(self, demos: list[type[HorrorDemo]], font: pyxel.Font | None = None):
        self.font = font
        self.demo_classes = demos
        self.catalog = [demo.catalog_entry(index) for index, demo in enumerate(demos)]
        self.current_demo_index = -1
        self.selected_demo: HorrorDemo | None = None
        self.hover_index = 0

    def update(self) -> None:
        if self.current_demo_index == -1:
            pyxel.mouse(True)
            self._update_menu_hover()
            self._update_menu_input()
            return

        if self.selected_demo is None:
            self.back_to_menu()
            return

        pyxel.mouse(self.selected_demo.uses_mouse)
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self.back_to_menu()
            return
        if pyxel.btnp(pyxel.KEY_R):
            self.restart_demo()
            return
        if not self.selected_demo.finished:
            self.selected_demo.update()

    def draw(self) -> None:
        if self.current_demo_index == -1:
            self._draw_menu()
            return

        if self.selected_demo is None:
            self._draw_menu()
            return

        self.selected_demo.draw()
        self.selected_demo.draw_hud()
        self.selected_demo.draw_outcome_overlay()

    def back_to_menu(self) -> None:
        self.current_demo_index = -1
        self.selected_demo = None

    def restart_demo(self) -> None:
        if self.current_demo_index != -1:
            self.selected_demo = self.demo_classes[self.current_demo_index](font=self.font)

    def select_demo(self, index: int) -> None:
        self.current_demo_index = index
        self.hover_index = index
        self.selected_demo = self.demo_classes[index](font=self.font)

    def draw_text(self, x, y, text, col):
        if self.font:
            pyxel.text(x, y, text, col, self.font)
        else:
            pyxel.text(x, y, text, col)

    def _update_menu_hover(self) -> None:
        for index, rect in enumerate(self._menu_rects()):
            if point_in_rect(pyxel.mouse_x, pyxel.mouse_y, rect):
                self.hover_index = index
                return

    def _update_menu_input(self) -> None:
        for index in range(len(self.catalog)):
            if pyxel.btnp(getattr(pyxel, f"KEY_{index + 1}")):
                self.select_demo(index)
                return

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            for index, rect in enumerate(self._menu_rects()):
                if point_in_rect(pyxel.mouse_x, pyxel.mouse_y, rect):
                    self.select_demo(index)
                    return

    def _menu_rects(self) -> list[tuple[int, int, int, int]]:
        return [(12, 34 + index * 24, SCREEN_WIDTH - 24, 20) for index in range(len(self.catalog))]

    def _draw_menu(self) -> None:
        pyxel.cls(0)
        self.draw_text(60, 10, "MICRO JAM 055", 7)
        self.draw_text(60, 18, "七场噩梦 (SEVEN NIGHTMARES)", 8 if (pyxel.frame_count // 20) % 2 == 0 else 10)
        self.draw_text(18, 28, "按 1-7 或点击一个房间开始（ESC 退出）", 6)

        rects = self._menu_rects()
        for entry, rect in zip(self.catalog, rects, strict=False):
            x, y, w, h = rect
            hover = entry.index == self.hover_index
            fill = 2 if hover else 1
            border = entry.accent_color if hover else 5
            draw_panel(x, y, w, h, fill, border)
            self.draw_text(x + 6, y + 5, f"{entry.index + 1}. {entry.title_cn} ({entry.title_en})", 7)
            self.draw_text(x + 180, y + 5, "鼠标" if entry.uses_mouse else "按键", 6)

        active = self.catalog[self.hover_index]
        draw_panel(0, PLAYFIELD_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT - PLAYFIELD_HEIGHT, 0, active.accent_color)
        self.draw_text(6, PLAYFIELD_HEIGHT + 4, f"{active.title_cn} ({active.title_en})", active.accent_color)
        draw_wrapped_text(6, PLAYFIELD_HEIGHT + 13, active.description_cn, 7, 30, font=self.font)
        self.draw_text(6, PLAYFIELD_HEIGHT + 27, f"目标: {active.goal_cn}", 6)
