from __future__ import annotations

import sys
from pathlib import Path

import pytest


class PyxelStub:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.frame_count = 0
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_visible = False
        self._down: set[str] = set()
        self._pressed: set[str] = set()

    def set_buttons(self, down: set[str] | None = None, pressed: set[str] | None = None) -> None:
        self._down = set(down or set())
        self._pressed = set(pressed or set())

    def btn(self, key: str) -> bool:
        return key in self._down

    def btnp(self, key: str) -> bool:
        return key in self._pressed

    def init(self, *args, **kwargs) -> None:
        self.init_args = (args, kwargs)

    def run(self, update, draw) -> None:
        self.run_callbacks = (update, draw)

    def mouse(self, visible: bool = True) -> None:
        self.mouse_visible = visible

    def rndi(self, low: int, high: int) -> int:
        return low

    def __getattr__(self, name: str):
        if name.startswith("KEY_") or name.startswith("MOUSE_"):
            return name

        def noop(*args, **kwargs):
            return None

        return noop


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PYXEL = PyxelStub()
sys.modules["pyxel"] = PYXEL


@pytest.fixture(autouse=True)
def reset_pyxel() -> PyxelStub:
    PYXEL.reset()
    yield PYXEL
    PYXEL.reset()


@pytest.fixture
def pyxel_stub() -> PyxelStub:
    return PYXEL
