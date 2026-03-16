import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import main
import unit_system


class ScenarioGame(main.Game):
    def _create_initial_units(self):
        return [
            unit_system.Unit(main.PLAYER_COMMANDER_ID, unit_system.Side.PLAYER, unit_system.UnitType.SPEAR, (4, 6), hp=100),
            unit_system.Unit(main.ENEMY_COMMANDER_ID, unit_system.Side.ENEMY, unit_system.UnitType.SPEAR, (5, 6), hp=100),
        ]


if __name__ == "__main__":
    ScenarioGame()
