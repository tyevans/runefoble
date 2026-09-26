# How-To: Add a Tool to The Watcher MCP Gateway

## Overview
The Watcher AI system exposes tools to external LLMs and internal agents via the Model Context Protocol (MCP) server located in `gateway/mcp/src/gateway_mcp/server.py`.

## Adding a New MCP Tool

### 1. Define the Tool Function
Open `gateway/mcp/src/gateway_mcp/server.py` and decorate your tool with `@mcp.tool()`:

```python
@mcp.tool()
def cast_spell(session_id: str, caster_id: str, spell_name: str, target_coords: dict) -> dict:
    """Cast a tactical spell, calculate AoE, and update affected tokens."""
    return {
        "status": "cast",
        "spell": spell_name,
        "area_affected": "radius_15ft",
        "narrative": f"Arcane energy ripples towards ({target_coords.get('x')}, {target_coords.get('y')})!",
    }
```

### 2. Add Type Annotations and Docstring
MCP clients (such as Claude Desktop, Gemini agents, or Antigravity) use function docstrings and type annotations to generate the tool definition schema. Ensure all parameters have descriptions.

### 3. Verify Tool Execution
Run the test suite or test locally:
```bash
uv run python gateway/mcp/src/gateway_mcp/main.py
```
