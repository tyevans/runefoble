# How-To: Add a Tool to The Watcher MCP Gateway

## Overview
The Watcher AI system exposes tools to external LLMs and internal agents via the Model Context Protocol (MCP) server located in `gateway/mcp/src/gateway_mcp/server.py`. Tools, resources, and prompt templates are organized into modular domain sub-packages under `gateway/mcp/src/gateway_mcp/`:
- `tools/`: Tabletop mechanics, dice, board mutations, character sheet actions, and action planning.
- `resources/`: Dynamic session state (`session://{session_id}/state`) and combat encounters (`encounter://{session_id}/current`). Each resource reads its owning service.
- `prompts/`: Narrative framing and tactical guidance prompts (`dm_narrative_guidance`, `tactical_action_adviser`).

## Adding a New MCP Tool

### 1. Define the Tool Function in the Appropriate Sub-Package
Locate the relevant domain module in `gateway/mcp/src/gateway_mcp/tools/` (e.g., `character.py`, `board.py`, or a new module).

A tool that owns no data must not return fixed data. It calls the owning service over HTTP:

```python
from gateway_mcp.clients import ServiceClient


async def inspect_tactical_board(session_id: str) -> dict:
    """Read tokens and grid dimensions for the session from board_state."""
    board = await ServiceClient().get_board(session_id)
    return {"session_id": session_id, "tokens": list(board["tokens"].values())}
```

Add a typed method to `gateway/mcp/src/gateway_mcp/clients/services.py` for each new upstream route. Use `self._request(...)`. It maps 5xx and connection failures to `ServiceUnavailableError`, and 4xx responses to `ServiceRejectedError`. Do not catch these errors in the tool. FastMCP reports them as MCP tool error results.

Add the base URL to `gateway/mcp/src/gateway_mcp/settings.py` and to the Helm `services.gatewayMcp` values when a new upstream service is added.

Only pure computation, such as dice rolls or rule lookups, may run inside the gateway without a service call. Tools that store state must go through the owning bounded context (ADR-0007).

### 2. Register with FastMCP in Module Registration Hook
Add the tool registration to the module's registration hook (e.g., `register_character_tools` in `tools/character.py`):

```python
def register_character_tools(mcp: FastMCP) -> None:
    """Register character and inventory tools on the FastMCP application."""
    mcp.tool()(cast_spell)
```

Service-backed tools are `async`. FastMCP awaits them.

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

Write service-backed tools as blackbox tests. Start the owning service with `tests/helpers/live_services.py` (`serve(app)`), set its URL environment variable, and call the tool through the MCP protocol (`call_tool` in `tests/test_blackbox_mcp_gateway.py`). Add an error case that points the URL at `closed_port_url()` or a `unavailable_app(503)` stand-in.
