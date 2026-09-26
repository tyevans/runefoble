# How-To: Add a Tool to The Watcher MCP Gateway

## Overview
The Watcher AI system exposes tools to external LLMs and internal agents via the Model Context Protocol (MCP) server located in `gateway/mcp/src/gateway_mcp/server.py`. Tools, resources, and prompt templates are organized into modular domain sub-packages under `gateway/mcp/src/gateway_mcp/`:
- `tools/`: Tabletop mechanics, dice, board mutations, character sheet actions, and action planning.
- `resources/`: Dynamic session state (`session://active`, `session://{session_id}/state`) and combat encounters (`encounter://current`).
- `prompts/`: Narrative framing and tactical guidance prompts (`dm_narrative_guidance`, `tactical_action_adviser`).

## Adding a New MCP Tool

### 1. Define the Tool Function in the Appropriate Sub-Package
Locate the relevant domain module in `gateway/mcp/src/gateway_mcp/tools/` (e.g., `character.py`, `board.py`, or a new module):

```python
def cast_spell(session_id: str, caster_id: str, spell_name: str, target_coords: dict) -> dict:
    """Cast a tactical spell, calculate AoE, and update affected tokens."""
    return {
        "status": "cast",
        "spell": spell_name,
        "area_affected": "radius_15ft",
        "narrative": f"Arcane energy ripples towards ({target_coords.get('x')}, {target_coords.get('y')})!",
    }
```

### 2. Register with FastMCP in Module Registration Hook
Add the tool registration to the module's registration hook (e.g., `register_character_tools` in `tools/character.py`):

```python
def register_character_tools(mcp: FastMCP) -> None:
    """Register character and inventory tools on the FastMCP application."""
    mcp.tool()(cast_spell)
```

Ensure the tool is re-exported in `gateway/mcp/src/gateway_mcp/tools/__init__.py` and included in `register_tools(mcp)`.

### 3. Add Type Annotations and Docstring
MCP clients (such as Claude Desktop, Gemini agents, or Antigravity) use function docstrings and type annotations to generate the tool definition schema. Ensure all parameters have descriptions.

### 4. Verify Tool Execution
Run the test suite or test locally:
```bash
uv run python gateway/mcp/src/gateway_mcp/main.py
```
And verify via pytest:
```bash
uv run pytest tests/test_mcp_tools.py tests/test_blackbox_mcp_gateway.py
```
