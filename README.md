# Micro Jam 055: Seven Nightmares

A Pyxel horror anthology built as seven short playable demos behind one selector menu.

## Requirements

- Python 3.12+
- `pyxel`
- `pytest`

Install the runtime and test dependencies with:

```bash
python -m pip install -r requirements.txt
```

## Run

Launch the anthology from the project root:

```bash
python main.py
```

Menu controls:

- `1`-`7` or mouse click: enter a demo
- `ESC`: return to the anthology menu
- `R`: restart the active demo after a failure or victory

Each demo shows its own objective and controls in the lower HUD.

## Test

The default pytest suite now targets the horror anthology only:

```bash
python -m pytest
```

Legacy SRPG files are still archived in `srpg_main.py`, `unit_system.py`, and the old `tests/test_main_*` / `tests/test_rewind.py` files, but they are no longer part of the default collection path.
