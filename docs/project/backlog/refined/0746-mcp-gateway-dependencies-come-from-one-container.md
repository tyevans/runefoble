---
id: '0746'
title: MCP Gateway Dependencies Come From One Container, Not Module Globals
status: Refined
created: 2026-11-17
dependencies:
- TASK-0532
- TASK-0545
- TASK-0745
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0022
governing_stories:
- US-0035
target_bc: gateway
target_release: 0.9.0
---
# TASK-0746: MCP Gateway Dependencies Come From One Container, Not Module Globals

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
The registry, event bus, SpiceDB client, and MCP instance are module-level singletons. Tests reset them by hand. The authorization guard imports HTTP and SpiceDB concretes.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/dynamic/registry.py:126` (`dynamic_registry = DynamicToolRegistry()`).
- `dynamic/events.py:12,24-27` (`_event_bus` global, `set_event_bus`) and `:14` (global pending task set).
- `dynamic/auth.py:12-26` (`_spicedb_client` global); `auth.py:8-9,70-73` imports `fastapi.HTTPException` and `runefoble_auth.spicedb` concretes in the guard.
- `tools/orchestration.py:17,86,150-151` (`_mcp_instance` global). `registry.py:46-49,78-79` use FastMCP private `_tool_manager`.
- Tests reset state by hand (`tests/test_blackbox_dynamic_mcp/conftest.py:57-62`, `tests/test_blackbox_uvtt_import/conftest.py:36-37`).

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- TASK-0532 and TASK-0545 change `dynamic/auth.py` and the router. Run this task after them.

## Product & User Story References
- PRD-0022
- US-0035

## Detailed Specification & Implementation Plan
1. Add `GatewayMcpContainer` (registry, event bus, `PermissionChecker` port, shared service clients) built in `server.py`. Pass it to `register_*` functions and to routers with `Depends`.
2. `auth.py` depends on a `PermissionChecker` port and raises a domain `PermissionDenied`. The router maps it to 403.
3. Put all FastMCP `_tool_manager` access in one adapter module.
4. Remove the globals. Tests build one container per test.

## Frontdoor Blackbox Test Plan
- Existing `tests/test_blackbox_dynamic_mcp/` passes with unchanged behaviour.
- New: two app instances keep separate registries.

## Definition of Done
- `grep -n "^[a-z_]* = .*Registry()\|global " gateway/mcp/src` finds no singleton.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `gateway-mcp.md (F3)`
