import pytest

from horror_engine.demos.demo1_abyssal import AbyssalEchoes
from horror_engine.demos.demo2_loop import ZeroHourLoop
from horror_engine.demos.demo3_flesh import FleshFactory
from horror_engine.demos.demo4_eyes import ForestOfEyes
from horror_engine.demos.demo5_glitch import GlitchFloor13
from horror_engine.demos.demo6_hunt import BloodMoonHunt
from horror_engine.demos.demo7_signal import SignalOfDespair


@pytest.mark.parametrize(
    "demo_cls",
    [
        AbyssalEchoes,
        ZeroHourLoop,
        FleshFactory,
        ForestOfEyes,
        GlitchFloor13,
        BloodMoonHunt,
        SignalOfDespair,
    ],
)
def test_demo_smoke_instantiation(demo_cls) -> None:
    demo = demo_cls()

    assert demo.title
    assert demo.goal
    assert demo.controls


def test_abyssal_echoes_ping_wakes_enemy() -> None:
    demo = AbyssalEchoes()

    demo.emit_pulse()

    assert demo.enemy_awake is True
    assert demo.ping_count == 1


def test_zero_hour_loop_breaks_after_all_anomalies() -> None:
    demo = ZeroHourLoop()
    demo.loops = 3
    for anomaly in demo.anomalies:
        ax, ay, _, _ = anomaly["rect"]
        demo.player_x = ax
        demo.player_y = ay
        demo.inspect_nearby_anomaly()

    demo.trigger_top_door()

    assert demo.outcome == "success"


def test_flesh_factory_sacrifice_costs_integrity() -> None:
    demo = FleshFactory()

    demo.sacrifice_leg()

    assert demo.leg_sacrificed is True
    assert demo.integrity == 70


def test_forest_of_eyes_detection_can_fail() -> None:
    demo = ForestOfEyes()
    demo.eye_state = 2
    demo.detection = 99
    demo.px = 10
    demo.py = 10

    demo.update()

    assert demo.outcome == "failure"


def test_glitch_floor_13_sequence_wins() -> None:
    demo = GlitchFloor13()
    for label in ["1", "3", "2", "13"]:
        demo.press_button(label)

    assert demo.outcome == "success"


def test_blood_moon_hunt_scares_villagers_in_darkness() -> None:
    demo = BloodMoonHunt()
    for torch in demo.torches:
        torch["on"] = False
    demo.visibility = 40
    demo.px = demo.villagers[0]["x"]
    demo.py = demo.villagers[0]["y"]

    for _ in range(8):
        demo.update()

    assert demo.villagers[0]["state"] == "fleeing"


def test_signal_of_despair_lock_wins() -> None:
    demo = SignalOfDespair()
    demo.frequency = demo.target_frequency

    for _ in range(120):
        demo.evaluate_signal()

    assert demo.outcome == "success"


def test_signal_of_despair_false_voice_loses() -> None:
    demo = SignalOfDespair()
    demo.frequency = demo.false_frequency

    for _ in range(90):
        demo.evaluate_signal()

    assert demo.outcome == "failure"
