# demo1

A new project created with Intent by Augment.

## Pyxel MCP Debug Setup

This project can use [`pyxel-mcp`](https://github.com/kitao/pyxel-mcp) during development for automated visual/debug checks.

### 1) MCP server config (already added)

Project root now includes `.mcp.json`:

```json
{
  "mcpServers": {
    "pyxel": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "pyxel-mcp", "pyxel-mcp"]
    }
  }
}
```

This uses `uvx` to run `pyxel-mcp` without requiring a global install.

### 2) Optional direct install

If you prefer a direct local install:

```bash
pip install pyxel-mcp
```

Then you can switch `.mcp.json` command to:

```json
{
  "mcpServers": {
    "pyxel": {
      "type": "stdio",
      "command": "pyxel-mcp"
    }
  }
}
```

### 3) Typical debug workflow

1. Start or iterate on your game code (`main.py`).
2. Use MCP tools such as:
   - `run_and_capture`
   - `play_and_capture`
   - `inspect_state`
   - `inspect_screen`
   - `compare_frames`
3. Validate gameplay behavior and visual changes frame-by-frame while developing.

### Notes

- Verified package availability on 2026-03-10: `pyxel-mcp` latest is `0.7.3`.
- `pyxel` is already available in this environment (`2.6.6`).
