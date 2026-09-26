# TASK-0005: Model Context Protocol (MCP) RPG Tools Expansion

## Description
Expand the FastMCP gateway in `gateway/mcp/src/gateway_mcp/server.py` to support comprehensive tabletop tool invocations: condition assignments, spell slot tracking, inventory inspection, and dynamic encounter creation.

## Governing Documents
- ADRs: ADR-0002, ADR-0007
- PRDs: PRD-0001
- User Stories: US-0008

## Definition of Done
1. FastMCP server exposes `cast_spell`, `modify_character_hp`, `add_condition`, and `query_encounter_state`.
2. All tools have strict type hints and docstrings compatible with Claude, Gemini, and local LLM clients.
3. Unit tests in `tests/test_mcp_tools.py` verify each tool schema and execution behavior.
4. Python tests pass and Ruff linting reports 0 errors.
