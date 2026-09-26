# TASK-0005: Model Context Protocol (MCP) RPG Tools Expansion

## Status
Complete

## Summary
Expanded the FastMCP server in `gateway/mcp/src/gateway_mcp/server.py` to support comprehensive tabletop tool invocations: condition assignments, spell slot tracking and effects, hit point adjustments (with bloodied/unconscious states), encounter queries, inventory inspections, and tactical encounter creation. Created unit tests in `tests/test_mcp_tools.py` verifying tool registration, parameter parsing, and responses.

## Key Changes
- `gateway/mcp/src/gateway_mcp/server.py`:
  - Added `cast_spell`: Validates spell levels (cantrips vs leveled slots), returns consumed slots and rules effects.
  - Added `modify_character_hp`: Handles positive/negative HP changes, conscious/bloodied/unconscious status thresholds.
  - Added `add_condition`: Applies D&D 5e / Pathfinder conditions (`blinded`, `prone`, `drunk`, `foolishness`, etc.) with rule effects.
  - Added `query_encounter_state`: Returns round number, active turn, initiative roster, and environmental hazards.
  - Added `inspect_inventory`: Returns equipped items, carried inventory, currency, and encumbrance.
  - Added `create_encounter`: Creates new combat encounters with terrain and enemy spawns.
  - Maintained strict typing and docstrings for Claude, Gemini, and local LLM MCP clients.
  - Kept file length at 306 lines (<500 lines limit).
- `tests/test_mcp_tools.py`:
  - Added 12 unit tests verifying schema registration and execution for every MCP tool.
- `tests/test_entrypoints.py`:
  - Updated tool registry test to verify all 11 MCP tools.

## Verification
- `uv run pytest`: 71/71 tests pass.
- `uv run ruff check .` & `uv run ruff format .`: Zero lint or format issues.
- `pnpm --dir frontend run build`: Clean build.
- `helm lint deployments/helm/runefoble`: 0 chart failures.
