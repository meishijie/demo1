from horror_engine.demos.demo1_abyssal import AbyssalEchoes
from horror_engine.demos.demo2_loop import ZeroHourLoop
from horror_engine.demos.demo3_flesh import FleshFactory
from horror_engine.demos.demo4_eyes import ForestOfEyes
from horror_engine.demos.demo5_glitch import GlitchFloor13
from horror_engine.demos.demo6_hunt import BloodMoonHunt
from horror_engine.demos.demo7_signal import SignalOfDespair
from horror_engine.manager import HorrorManager


DEMO_CLASSES = [
    AbyssalEchoes,
    ZeroHourLoop,
    FleshFactory,
    ForestOfEyes,
    GlitchFloor13,
    BloodMoonHunt,
    SignalOfDespair,
]


def test_catalog_metadata_is_precomputed() -> None:
    manager = HorrorManager(DEMO_CLASSES)

    assert [entry.title for entry in manager.catalog] == [
        "Abyssal Echoes",
        "Zero Hour Loop",
        "The Flesh Factory",
        "Forest of Eyes",
        "Glitch: Floor 13",
        "Blood Moon Hunt",
        "Signal of Despair",
    ]


def test_menu_click_selects_demo(pyxel_stub) -> None:
    manager = HorrorManager(DEMO_CLASSES)
    pyxel_stub.mouse_x = 20
    pyxel_stub.mouse_y = 40
    pyxel_stub.set_buttons(pressed={pyxel_stub.MOUSE_BUTTON_LEFT})

    manager.update()

    assert manager.current_demo_index == 0
    assert isinstance(manager.selected_demo, AbyssalEchoes)


def test_restart_and_back_to_menu() -> None:
    manager = HorrorManager(DEMO_CLASSES)
    manager.select_demo(4)
    first_instance = manager.selected_demo

    manager.restart_demo()

    assert isinstance(manager.selected_demo, GlitchFloor13)
    assert manager.selected_demo is not first_instance

    manager.back_to_menu()

    assert manager.current_demo_index == -1
    assert manager.selected_demo is None
