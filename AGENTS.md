# Project Agents Guide / 项目 Agent 指南

This file applies to the whole repository.
本文件作用于整个仓库，供后续 AI coding agent 直接遵循。

## Project Overview / 项目概览

- This is a Pyxel-based SRPG prototype.
- Main game entry point: `main.py`
- Combat, terrain, movement, and rules: `unit_system.py`
- Automated tests: `python3 -m unittest discover -s tests -q`

- 本项目是一个基于 Pyxel 的 SRPG 原型。
- 游戏主入口文件：`main.py`
- 战斗、地形、移动与规则模块：`unit_system.py`
- 自动化测试命令：`python3 -m unittest discover -s tests -q`

## Pyxel MCP / Pyxel MCP 约定

- This repository is already configured for Pyxel MCP in `.mcp.json`.
- Preferred server command: `uvx --from pyxel-mcp pyxel-mcp`
- If the active Python environment does not have Pyxel MCP available, install it with:
  `python3 -m pip install pyxel-mcp`

- 当前仓库已经在 `.mcp.json` 中接入 Pyxel MCP。
- 首选启动命令：`uvx --from pyxel-mcp pyxel-mcp`
- 如果当前 Python 环境没有安装，可执行：
  `python3 -m pip install pyxel-mcp`

## When To Use Pyxel MCP / 何时必须使用 Pyxel MCP

Use Pyxel MCP proactively whenever a change affects visible or interactive game behavior, especially:

- map rendering
- camera movement or edge scrolling
- unit placement, movement range, attack highlights, hover UI, or HUD text
- turn flow, button states, victory state, or other screen-visible state
- input-driven behavior such as clicking units or ending the turn

Do not rely on static code inspection alone for these changes when a capture-based check is feasible.

凡是修改会影响“画面可见结果”或“交互行为”的内容，都应主动使用 Pyxel MCP 验证，尤其包括：

- 地图渲染
- 镜头移动或靠边滚动
- 单位摆放、移动范围、高亮、悬停信息窗、HUD 文本
- 回合切换、按钮状态、胜负状态等可见状态
- 点击单位、结束回合等输入驱动行为

如果能够通过截图或输入回放验证，就不要只靠静态读代码下结论。

## Verification Workflow / 验证流程

After visual or gameplay changes, prefer this order:

1. Run tests: `python3 -m unittest discover -s tests -q`
2. Capture a baseline screen with `run_and_capture("main.py", frames=30, scale=2, timeout=20)`
3. For input-dependent behavior, use `play_and_capture`
4. For logic debugging, use `inspect_state`
5. For visual regressions, use `compare_frames` or `inspect_screen`

涉及视觉或玩法修改时，优先按下面顺序验证：

1. 跑测试：`python3 -m unittest discover -s tests -q`
2. 用 `run_and_capture("main.py", frames=30, scale=2, timeout=20)` 抓基线画面
3. 输入相关行为用 `play_and_capture`
4. 逻辑排查用 `inspect_state`
5. 视觉回归对比用 `compare_frames` 或 `inspect_screen`

## Capture Artifacts / 截图产物

- Save temporary verification screenshots under `artifacts/`
- Include the capture result in the final work summary when it was used for validation
- Reuse the existing MCP setup instead of creating a second parallel configuration

- 验证截图统一放在 `artifacts/`
- 只要本次工作用到了 Pyxel MCP，最终说明里要写明验证结果
- 复用现有 MCP 配置，不要再新建一套并行配置

### Known Baseline / 当前已知基线

- Frame-30 capture is known-good when it shows:
  `TURN: PLAYER`, `End Turn`, terrain rendering, and `Player turn: choose a unit`

- 当前已知可通过的基线截图为 frame 30，至少应看到：
  `TURN: PLAYER`、`End Turn`、地形渲染，以及 `Player turn: choose a unit`

## SRPG Acceptance Checklist / 当前 SRPG 原型验收要点

When implementing or reviewing features, treat the following as the active acceptance checklist:

1. The prototype runs stably at `320x192` and uses a `16x16` tile battlefield view.
2. The logical map size is `40x40`, with mouse edge scrolling to inspect the full map.
3. Terrain includes plain, forest, river, and sea; river and sea are impassable.
4. Both player and enemy sides exist, and both commanders are spear units.
5. Spear, cavalry, and archer advantage rules plus terrain modifiers affect combat results.
6. Archer units support ranged attacks up to 3 tiles.
7. ZOC rules create visible movement restrictions.
8. The prototype supports player turn, enemy turn, and manually ending the turn.
9. Hovering a unit shows an information panel with the intended font behavior.
10. Defeating the opposing commander ends the battle with a win or loss result.

后续实现或验收功能时，应以以下清单作为当前有效验收标准：

1. 原型在 `320x192` 下稳定运行，主战场采用 `16x16` 图块显示。
2. 地图逻辑大小为 `40x40`，支持鼠标靠边滚动查看全图。
3. 地形包含平地、森林、河流、海洋，其中河流和海洋不可进入。
4. 同时存在玩家队和敌军队，且双方大将均为枪兵。
5. 枪兵、骑兵、弓兵克制关系以及地形修正会影响战斗结算。
6. 弓兵具备最远 3 格远程攻击能力。
7. ZOC 规则会带来可观察的移动限制。
8. 支持玩家回合、敌方回合，以及手动结束回合。
9. 悬停单位会显示信息窗，并满足当前字体显示要求。
10. 击败对方大将会结束战斗并给出胜负结果。

## Working Style / 工作方式

- Make small changes, then verify them.
- When a task changes gameplay presentation, mention both test results and Pyxel MCP verification results.
- If a change touches the interface contract between `main.py` and `unit_system.py`, verify both code paths and visible behavior.

- 采用小步修改、立即验证的方式推进。
- 只要改动影响玩法呈现，结果说明里同时写测试结果和 Pyxel MCP 验证结果。
- 如果改动触及 `main.py` 与 `unit_system.py` 的接口契约，既要验证代码逻辑，也要验证实际画面行为。
