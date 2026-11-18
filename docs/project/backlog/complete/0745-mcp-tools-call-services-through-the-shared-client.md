---
id: '0745'
title: MCP Tools Call Owning Services Through the Shared Service Client
status: Complete
created: 2026-11-17
dependencies:
- TASK-0744
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0022
governing_stories:
- US-0008
target_bc: gateway
target_release: 0.9.0
---
# TASK-0745: MCP Tools Call Owning Services Through the Shared Service Client

## Status
Complete

## Summary
The MCP gateway keeps a second service client. It opens a new HTTP client per request, drops trace context, and builds some URL paths from unquoted agent input.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/clients/services.py:62-323` (removed) is a second `ServiceClient`. The shared client is `libs/runefoble_platform/src/runefoble_platform/service_client/client.py`.
- `services.py:91` opens a new `httpx.AsyncClient` per request. 15 tool sites call `ServiceClient()` inline (for example `tools/board.py:67,79,103,119` (removed), `tools/character.py:18,28,51,69,88,132` (removed)).
- `grep traceparent gateway/mcp/src` finds nothing, so MCP spans break at the service boundary.
- Unquoted agent input in paths at `services.py:127`, `:160`, `:249`, `:275`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- `docs/reference/service-client.md`, `docs/how-to/call-owning-services-through-the-gateway.md`, `docs/reference/fastmcp-gateway.md`.

## Product & User Story References
- PRD-0022
- US-0008

## Detailed Specification & Implementation Plan
1. Replace `ServiceClient()` in each tool with route helpers on the shared client from TASK-0744, using the path helper for every agent-supplied segment.
2. Map `UpstreamUnavailableError` and `UpstreamFailureError` to MCP tool errors. Keep the 5.0 s timeout.
3. Delete `gateway/mcp/src/gateway_mcp/clients/` (removed) completely.
4. Files: `tools/board.py` (removed), `tools/character.py` (removed), `tools/compendium.py` (removed), `gateway/mcp/src/gateway_mcp/tools/orchestration.py`, `resources/session.py`, `server.py`. Keep one shared client per base URL: container wiring is TASK-0746.

## Frontdoor Blackbox Test Plan
- Extend the MCP HTTP blackbox tests with a loopback upstream. Assert each call carries the service credential and `traceparent`.
- `inspect_tactical_board` with a `session_id` containing `/`: the upstream receives no other route and the tool returns an error.

## Definition of Done
- `gateway/mcp/src/gateway_mcp/clients/` (removed) no longer exists.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: high
- Source audits: `gateway-mcp.md (F2)`
