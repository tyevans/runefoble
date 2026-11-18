---
id: '0727'
title: Dynamic Tool Admin Routes Run in the MCP Gateway Process
status: Complete
created: 2026-11-17
dependencies:
- TASK-0532
- TASK-0545
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0022
governing_stories:
- US-0035
target_bc: gateway
target_release: 0.9.0
---
# TASK-0727: Dynamic Tool Admin Routes Run in the MCP Gateway Process

## Status
Complete

## Summary
The API gateway mounts the dynamic tool admin router in its own process. The MCP server runs in a separate container and never sees a tool that is registered through that router. The call succeeds and the tool does not appear for MCP clients.

## Problem Statement
- `gateway/api/src/gateway_api/main.py:49-50` imports `set_event_bus` and `tools_registry_router` from `gateway_mcp`. `main.py:110-111` mounts the router twice (at `/` and at `/api/v1`).
- `gateway/mcp/src/gateway_mcp/dynamic/registry.py:45` writes to FastMCP only when `self.mcp is not None`. `set_mcp_server` is called only in `gateway/mcp/src/gateway_mcp/server.py:54`. The API gateway process never calls it.
- `gateway/mcp/src/gateway_mcp/asgi.py` serves the MCP app only. It does not mount `tools_registry_router`. `Makefile` and `deployments/helm/runefoble/templates/gateway-mcp.yaml` run the MCP gateway as its own container.
- Effect: `POST /mcp/tools/register` on the API gateway stores the tool in a registry that the MCP process never reads. No error is raised.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- `docs/reference/fastmcp-gateway.md` and `docs/how-to/add-a-watcher-ai-tool.md` (dynamic registry section). Correct the route paths there.
- ADR-0015 (b): the gateway is thin. A route that must stay on the API gateway is a proxy through the shared service client.

## Product & User Story References
- PRD-0022
- US-0035

## Detailed Specification & Implementation Plan
1. Mount `tools_registry_router` on the MCP ASGI app in `gateway/mcp/src/gateway_mcp/asgi.py`. Keep one `DynamicToolRegistry` owner in the MCP process.
2. Remove the `gateway_mcp` router and `set_event_bus` imports and both `include_router` calls from `gateway_api/main.py`. If the API gateway must expose the admin routes, replace them with a proxy through `forward_json`. Choose one and state it in the PR.
3. Update all call sites and docs to the new route. Add no alias route (DoR 9).
4. Run this task after TASK-0532 and TASK-0545 land, because they edit the same router and mounts.

## Frontdoor Blackbox Test Plan
- Register a tool through the public admin route. Then call MCP `tools/list` and `tools/call` on the MCP endpoint. Assert that the tool appears and runs.
- If the route leaves the API gateway: assert that the API gateway returns 404 for the old path.

## Definition of Done
- A tool registered through the public admin route is visible and callable over MCP.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: high
- Source audits: `gateway-mcp.md (F1)`
