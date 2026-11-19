---
id: '0861'
title: Owner Paths Come From One Route Table in the Shared Library
status: Complete
created: 2026-11-18
dependencies:
- TASK-0746
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: gateway
target_release: 0.9.0
---
# TASK-0861: Owner Paths Come From One Route Table in the Shared Library

## Status
Complete

## Summary
Owner paths are defined in three styles. `libs/runefoble_platform/src/runefoble_platform/service_client/owner_routes.py` has nine routes. The MCP `OwningServices` builds seven more paths inline. The gateway character routes build paths with a helper, `character_path` in `character_view.py`. The proxy table uses `owner_segments`. The fix adds the missing routes to `owner_routes` and makes every caller use it. Wire paths do not change.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/service_client/owner_routes.py`: nine owner routes.
- `gateway/mcp/src/gateway_mcp/owning_services.py:166`, `:172`, `:176`, `:185`, `:192`, `:306`, `:312`: inline `path("api", "v1", ...)`.
- `gateway/api/src/gateway_api/character_view.py:22-27`: `CHARACTERS_PATH` and `character_path`. Used by `routers/characters_subresources_proxy.py` (lines 57, 86, 103, 133).
- `gateway/api/src/gateway_api/proxy_table.py`: rows use `owner_segments`.

## Documentation & Architecture Review
- The comment in `proxy_table.py` (lines 4-8) says owner paths have one definition in `owner_routes`. The code does not match it. Fix the code.
- ADR-0015 (b): one shared, typed service client.
- `docs/reference/service-client.md`: update it to match.
- TASK-0746 (refined) changes `owning_services.py`. Land it first.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add the missing owner routes (boards, sessions, combat start and read, narrate, propose) to `owner_routes.py`.
2. Replace each inline path in `owning_services.py` with the table entry.
3. Replace `character_path` with `owner_routes` entries. Delete `CHARACTERS_PATH` if no caller remains.
4. Keep `owner_segments` only for rows that have no `owner_routes` entry. Document the reason in the module docstring.
5. Compare the wire paths before and after. They must match.

## Frontdoor Blackbox Test Plan
- Existing gateway proxy tests that assert the upstream path pass.
- Add an assertion that each row in the route ownership page still matches a mounted route.
- MCP tests with a live upstream double (see `docs/how-to/test-cross-service-calls-with-live-upstreams.md`) pass for `create_board`, `get_board`, and `start_combat`.

## Definition of Done
- Each owner path is defined once.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `refactor-r2/gateways.md` (F5)
