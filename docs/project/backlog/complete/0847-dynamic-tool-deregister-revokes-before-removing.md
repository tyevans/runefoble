---
id: '0847'
title: Dynamic Tool Deregistration Revokes Permissions Before It Removes the Tool
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: gateway
target_release: 0.9.0
---
# TASK-0847: Dynamic Tool Deregistration Revokes Permissions Before It Removes the Tool

## Status
Complete

## Summary
The DELETE route for a dynamic MCP tool removes the registry entry first and then revokes the SpiceDB author relation. The revoke has no error mapping. When SpiceDB is down, the caller gets a 500, the tool is already gone, and the author tuple stays. A retry returns 404. The fix revokes first, maps the error the same way as grant, and removes the registry entry only after revoke succeeds.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/routers/tools_registry.py:110-113`: `dynamic_registry.deregister_tool(tool_name)` runs before `revoke_tool_permissions`.
- `gateway/mcp/src/gateway_mcp/dynamic/auth.py:38-47`: `revoke_tool_permissions` does not catch `AuthzError`.
- `dynamic/auth.py:23-36`: `grant_tool_permissions` maps `AuthzError` to `authorization_unavailable()`. Deregister has no such mapping.

## Documentation & Architecture Review
- ADR-0015 (b): the gateway returns 502 or 503 when an upstream fails. It never returns a substitute value.
- `docs/how-to/add-a-watcher-ai-tool.md` and `docs/reference/fastmcp-gateway.md` describe dynamic tool registration. Update them if the status codes are listed.
- TASK-0746 changes the SpiceDB default in `dynamic/auth.py`. Coordinate the edit; the two changes touch the same file.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. In `deregister_dynamic_tool`, call `revoke_tool_permissions` first, then `dynamic_registry.deregister_tool`.
2. In `revoke_tool_permissions`, catch `AuthzError` and raise `authorization_unavailable()`, as grant does.
3. If revoke fails, the registry entry stays. The caller can retry with the same result.
4. Do not add a fallback that removes the tool without revoking.

## Frontdoor Blackbox Test Plan
- Create a dynamic tool through the public MCP route with an author. Make the SpiceDB write fail (the existing authz test double). Send DELETE. Assert 503 with `authorization_unavailable`. Assert `GET` still lists the tool.
- Restore SpiceDB. Send DELETE again. Assert 200 and that `GET` returns 404.
- Assert the author relation is absent after success, through the public permission check.

## Definition of Done
- Revoke runs before registry removal. Revoke failure returns 503 and keeps the tool.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r2/gateways.md` (F6)
