# How-To: Add a Tool to The Watcher MCP Gateway

## Overview
The Watcher AI system exposes tools to external LLMs and internal agents via the Model Context Protocol (MCP) server built by `build_mcp(container)` in `gateway/mcp/src/gateway_mcp/server.py`. Each app gets one `GatewayMcpContainer` (`gateway/mcp/src/gateway_mcp/container.py`). The container holds the dynamic tool registry, the permission port, and the service client pool. Tools receive the container as their first argument. No module keeps these as a global (TASK-0746). Tools, resources, and prompt templates are organized into modular domain sub-packages under `gateway/mcp/src/gateway_mcp/`:
- `tools/`: Tabletop mechanics, dice, board mutations, character sheet actions, and action planning.
- `resources/`: Dynamic session state (`session://{session_id}/state`) and combat encounters (`encounter://{session_id}/current`). Each resource reads its owning service.
- `prompts/`: Narrative framing and tactical guidance prompts (`dm_narrative_guidance`, `tactical_action_adviser`).

## Adding a New MCP Tool

### 1. Define the Tool Function in the Appropriate Sub-Package
Locate the relevant domain module in `gateway/mcp/src/gateway_mcp/tools/` (e.g., `character.py`, `board.py`, or a new module).

A tool that owns no data must not return fixed data. It calls the owning service over HTTP:

```python
from gateway_mcp.container import GatewayMcpContainer
from gateway_mcp.owning_services import OwningServices


async def inspect_tactical_board(container: GatewayMcpContainer, session_id: str) -> dict:
    """Read tokens and grid dimensions for the session from board_state."""
    board = await OwningServices(container.service_clients).get_board(session_id)
    return {"session_id": session_id, "tokens": list(board["tokens"].values())}
```

Add a typed method to `OwningServices` in `gateway/mcp/src/gateway_mcp/owning_services.py` for each new upstream route. Build the route with `path(...)` from `runefoble_platform.service_client`, so that every agent-supplied segment stays inside one segment. Call `self._json(service, method, route, body)`. It sends through the shared service client of the container (`container.service_clients`). It maps 5xx and connection failures to `ServiceUnavailableError`, and 4xx responses to `ServiceRejectedError`. Do not catch these errors in the tool. FastMCP reports them as MCP tool error results.

Add the base URL to `gateway/mcp/src/gateway_mcp/settings.py` and, in Helm, add `gateway-mcp` to the `consumers` list of the upstream's entry under `services` in `deployments/helm/runefoble/values.yaml`.

Only pure computation, such as dice rolls or rule lookups, may run inside the gateway without a service call. Tools that store state must go through the owning bounded context (ADR-0007).

### 2. Register with FastMCP in Module Registration Hook
Add the tool registration to the module's registration hook (e.g., `register_character_tools` in `gateway/mcp/src/gateway_mcp/tools/character.py`). The hook takes the container and binds it to the tool with `bind_container`. FastMCP then sees the tool without the container parameter:

```python
def register_character_tools(mcp: FastMCP, container: GatewayMcpContainer) -> None:
    """Register character and inventory tools on the FastMCP application."""
    mcp.tool()(bind_container(cast_spell, container))
```

Service-backed tools are `async`. FastMCP awaits them.

For a new tool module, call its registration hook from `build_mcp(container)` in `gateway/mcp/src/gateway_mcp/server.py`. Import the hook from its defining module. The package `__init__.py` files hold only a docstring and export no names.

### 3. Add Type Annotations and Docstring
MCP clients (such as Claude Desktop, Gemini agents, or Antigravity) use function docstrings and type annotations to generate the tool definition schema. Ensure all parameters have descriptions.

### 4. Verify Tool Execution
The MCP transport needs a verified bearer token on every request. A client that sends none gets `401` before any tool runs (ADR-0015 c, TASK-0532). Send `Authorization: Bearer <token>` with each MCP request. Tools read the caller from that verified request, never from a header or argument. See `docs/reference/fastmcp-gateway.md`.

Run the test suite or test locally. Export the upstream URLs first, because the process refuses to start without them:
```bash
uv run python -m gateway_mcp.main
```
And verify via pytest:
```bash
uv run pytest tests/test_mcp_tools.py tests/test_blackbox_mcp_gateway.py
```

Write service-backed tools as blackbox tests. Start the owning service with `tests/helpers/live_services.py` (`serve(app)`), set its URL environment variable, and call the tool through the MCP protocol (`call_tool` in `tests/test_blackbox_mcp_gateway.py`). Add an error case that points the URL at `closed_port_url()` or a `unavailable_app(503)` stand-in.

### Check a Permission in a Mutating Tool
A tool that changes state must name one schema permission. Add `ctx: Context | None = None` to the tool. Call `await authorize_tool_call(ctx, container.permissions, requirement)` from `gateway_mcp.tool_authz` before any service call. Build the requirement with a helper such as `dm_action_on_character`, `character_edit`, `token_move`, or `session_control`. Add a builder to `_STEP_BUILDERS` in the same module, so that `execute_agent_action_plan` checks the tool too. Pass `OwningServices(container.service_clients, bearer=caller_bearer(ctx))`. Never read the caller from an argument. Write a test where a player is denied and the DM succeeds.

### 5. Call the Tool with a Bearer Token
In a blackbox test, mint a token with the shared signing issuer and pass it to the MCP client. `tests/helpers/mcp_http.py` provides `call_tool_over_http(endpoint, name, arguments, bearer=...)`. Do not send an `X-User-Id` header or a caller field in the arguments.

## Authorize a New Watcher Route

A tool that calls a new Watcher HTTP route inherits that route's checks. Every Watcher route must follow these rules:

1. Take the caller from the verified token. Add `caller_id: CallerId` (from `the_watcher.identity`). Never read `X-User-Id`, a query parameter, or a body field for identity.
2. Pick the permission that the action needs. Use a key of `runefoble_auth.contract.ACTION_PERMISSIONS`. Add the key there if it is missing, and make sure the schema defines the permission.
3. Call the matching helper first in the handler:
   - `require_session_permission(caller_id, session_id, "session.control")` for DM actions, or `"session.participate"` for player actions, or `"session.observe"` for read-only views.
   - `require_campaign_permission(caller_id, campaign_id, "campaign.run_session")` for campaign-wide DM actions, or `"campaign.view"` for campaign reads.
   - `require_dm(caller_id, campaign_id, session_id)` when a handler accepts either scope.
4. Do not compare role names or add `if not caller: return` branches. A missing principal gets HTTP 401 from the router dependency. A denied check gets HTTP 403.

Tests for the route set up the caller through schema tuples. Write `campaign:<id>#dungeon_master@user:<id>` and `game_session:<id>#campaign@campaign:<id>` with `bind_session_to_campaign` or `make_table_runner` from `tests/helpers/spicedb_factory.py`.
