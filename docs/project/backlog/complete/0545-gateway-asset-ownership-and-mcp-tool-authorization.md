---
id: '0545'
title: Gateway Asset Ownership and MCP Tool Authorization
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0541
- TASK-0542
- TASK-0521
- TASK-0532
governing_adrs:
- ADR-0001
- ADR-0007
governing_prds:
- PRD-0022
- PRD-0009
governing_stories:
- US-0035
- US-0008
- US-0038
target_release: 0.9.0
---

# TASK-0545: Gateway Asset Ownership and MCP Tool Authorization

## Status
Complete

## Summary
The gateway MCP registry lets anonymous callers register, overwrite, delete, and run dynamic tools. The author comes from the request body. The static MCP tools that change penalties, hit points, or board tokens have no caller check. The asset upload and delete routes on the gateway have no check, and delete takes the raw bearer value as a user id. This task makes each mutating MCP and asset route require a verified principal and a schema permission.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/dynamic/auth.py:63-64`: `enforce_tool_auth` returns without a check when `user_id` is falsy. Probe: anonymous register returns 200, and anonymous delete of another author's tool returns 200 (`w1-gateway-mcp.md` F2).
- `gateway/mcp/src/gateway_mcp/routers/tools_registry.py:38-108`: `author_id` is `payload.author_id or x_user_id`, so the body chooses the author. Execute accepts the caller from a body field (`w3-authz-coverage.md` F8).
- `gateway/mcp/src/gateway_mcp/routers/tools_registry.py` is mounted at root and under `/api/v1` (`gateway/api/src/gateway_api/main.py:88-90`), with no auth dependency (`w1-gateway-mcp.md` F2).
- `gateway/mcp/src/gateway_mcp/tools/character.py` (`apply_absentee_penalty`, `modify_character_hp`, `cast_spell`, `add_condition`) and `tools/board.py` (`move_board_token`, `create_encounter`): no caller identity and no SpiceDB check. `tools/orchestration.py:25-130` runs any registered tool with no identity (`w1-gateway-mcp.md` F5).
- `gateway/api/src/gateway_api/assets.py:85` (`POST /upload`): no auth dependency. `:237` (`DELETE /{asset_id}`): no SpiceDB check. `_resolve_user_id` (lines 71-82) returns the raw bearer value as the user id (`w1-gateway-api.md` F5).

## Documentation & Architecture Review
- ADR-0001: `mcp_tool` and `forged_asset` objects in `runefoble.zed` own these checks. `mcp_tool.manage` covers register, update, and delete. `mcp_tool.execute` covers execute. `forged_asset.manage` covers asset delete.
- ADR-0007: the MCP gateway does not own tool state. Tool definitions are the MCP context's responsibility. The gateway checks access and routes.
- `docs/reference/fastmcp-gateway.md` lists tools and their auth. Update it.
- `docs/how-to/add-a-watcher-ai-tool.md` describes adding tools. Add the required permission to the recipe.
- Out of scope and recorded in the index: the sandbox `exec` at `gateway/mcp/src/gateway_mcp/sandbox.py:155` remains in the request path after this task. A separate task must remove it.

## Product & User Story References
- US-0035 (runtime MCP tool hot reloading). US-0008 (MCP tool invocation for agents). US-0038 (procedural battlemaps and tokens, which uses asset ownership).

## Detailed Specification & Implementation Plan
1. MCP registry routes. TASK-0532 supplies the verified principal and removes the body author fields. This task adds the permission checks and tuple writes:
   - The author is the principal from TASK-0532.
   - On register: check `mcp_tool.manage` for an existing tool. For a new tool, write `mcp_tool:<id>#author@user:<principal>` and `mcp_tool:<id>#campaign@campaign:<cid>` through the library factory. A write error returns 503.
   - On update and deregister: check `mcp_tool.manage`.
   - On execute: check `mcp_tool.execute`.
   - Remove the overwrite exception that applies only when the header is present.
2. Static tools: each mutating tool receives the caller identity from the MCP request context. Each checks one permission before it calls a service:
   - `apply_absentee_penalty`, `modify_character_hp`, `add_condition`: `campaign.run_session` (DM action).
   - `cast_spell`: `character.edit`.
   - `move_board_token`: `board_token.move`.
   - `create_encounter`: `session.control`.
   - `execute_agent_action_plan`: checks each step's permission. A denied step stops the plan with a per-step error.
3. Assets (`gateway/api/src/gateway_api/assets.py`). TASK-0521 supplies the principal and removes `_resolve_user_id`. This task adds:
   - `POST /upload` writes the creator and campaign relations for the principal.
   - `DELETE /{asset_id}` requires `forged_asset.manage`.
4. Remove the `user-default` fallback in asset code.

## Frontdoor Blackbox Test Plan
- Anonymous `POST /mcp/tools/register` returns 401. Before the fix it returns 200.
- A user registers a tool. A second user calls `DELETE /mcp/tools/{name}` and gets 403. The first user gets 200.
- A body with `author_id` set to another user does not change the author. Read back the tool through the public registry route and check `author` is the principal.
- A player calls `apply_absentee_penalty` through the MCP tool endpoint and gets a permission error. The DM gets success.
- Anonymous `DELETE /api/v1/assets/{id}` returns 401. A non-creator with no campaign manage right gets 403. The creator gets 200.
- Setup for tools and assets goes through their public upload and register routes.

## Definition of Done
1. Frontdoor tests exist in `tests/test_blackbox_mcp_asset_authz.py` and pass.
2. `grep -rn "author_id\|user-default\|_resolve_user_id" gateway/` returns nothing in the production paths changed here.
3. `docs/reference/fastmcp-gateway.md` and `docs/how-to/add-a-watcher-ai-tool.md` describe the required permission per tool.
4. `uv run pytest gateway/mcp` and `uv run pytest tests/test_blackbox_mcp*` pass. `uv run ruff check gateway` passes.
5. The sandbox `exec` removal is listed in the index report as a follow-up, not done here.
6. No file in the change exceeds 500 lines.

## Audit Provenance

- Severity: critical
- Source audits: `w3-authz-coverage.md`, `w1-gateway-mcp.md`, `w1-gateway-api.md`

## Orchestrator Addenda (2026-11-17, refactor-r1)

- TASK-0545 (MCP and asset authorization): append "No task owns removal of the sandbox `exec` at `gateway/mcp/src/gateway_mcp/sandbox.py:155`. File one (not in this range). TASK-0737 follows its decision."

## Orchestrator Addenda (2026-11-17, round 3)

- Tool-to-tool calls in declarative dynamic-tool handlers (ADR-0020, TASK-0766) are not built. This task defines their authorization rule: a step that calls another tool checks `mcp_tool.execute` for the caller on that tool. Build the call step here or in a follow-up.
