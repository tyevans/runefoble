---
id: '0603'
title: Gateway MCP Board and Encounter Tools Call Owning Service Frontdoors
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0022
governing_stories:
- US-0008
- US-0035
target_release: 0.9.0
---

# TASK-0603: Gateway MCP Board and Encounter Tools Call Owning Service Frontdoors

## Status
Complete

## Summary
The MCP board and encounter tools return fixed data and persist nothing. Replace them with HTTP calls to the owning service (`board_state`, `rules_compendium` for encounter balance) through their public routes. Remove the canned dictionaries.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/tools/board.py:10-48`: `inspect_tactical_board` returns a fixed three-token list.
- `board.py:67-85`: `query_encounter_state` returns fixed round and initiative.
- `board.py:88-107`: `create_encounter` returns a random id. Nothing is stored.
- `board.py` also contains `move_board_token` and `calculate_encounter_balance` which must be checked for the same pattern.
- An agent that moves a token sees no change in board state.

Source: `.audit/reports/w1-gateway-mcp.md` F1. Existing task TASK-0005 (complete) shipped the canned set. TASK-0466 and TASK-0472 (proposed) add tools and do not wire existing ones.

## Documentation & Architecture Review
- `docs/reference/fastmcp-gateway.md`: tool inventory. Update the statement that tools are backed by services.
- `docs/how-to/add-a-watcher-ai-tool.md`: describes the tool pattern. Correct it to HTTP-backed calls.
- ADR-0007: the gateway MCP is an adapter. Domain state stays in `board_state`.
- Shared client helper: place the HTTP client in `gateway/mcp/src/gateway_mcp/clients/` (new module). Shared with TASK-0604 and TASK-0605.

## Product & User Story References
- `docs/project/user_stories/accepted/us-0008-mcp-tool-invocation-for-agents.md`
- `docs/project/user_stories/accepted/us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md`
- `docs/project/product/accepted/prd-0022-extensible-modder-platform-and-mcp-registry.md`

## Detailed Specification & Implementation Plan
1. Add `gateway_mcp/clients/services.py` with a typed async HTTP client. Base URLs come from settings (`BOARD_STATE_URL`, `RULES_COMPENDIUM_URL`). Map upstream errors to MCP tool errors. No fallback data.
2. Rewrite `inspect_tactical_board`, `query_encounter_state`, `create_encounter`, `move_board_token` to call `board_state` routes.
3. `calculate_encounter_balance` calls the `rules_compendium` public route.
4. Delete the canned dictionaries and the random id generator from `board.py`.
5. Add settings and Helm values for the two URLs (`deployments/helm/runefoble/values.yaml`).
6. Update `docs/reference/fastmcp-gateway.md` and `docs/reference/ports-and-endpoints.md` if they list these URLs.

## Frontdoor Blackbox Test Plan
- Before fix: call `create_encounter` through the MCP protocol, then call `query_encounter_state`. The state does not match (test fails).
- After fix: `move_board_token` followed by `inspect_tactical_board` through MCP returns the moved token position. The position is read from the board service.
- After fix: when the board service returns 503, the MCP tool returns an error result, not canned data.
- Tests start the real board service in-process through its public app or HTTP, and call the MCP protocol endpoint. They do not patch the client.

## Definition of Done
1. `board.py` contains no fixed token list, fixed round, or random id.
2. Client module in place. Files under 500 lines.
3. Blackbox tests pass. `uv run pytest gateway/mcp tests/test_blackbox_mcp_gateway.py` passes.
4. Ruff check and format pass.
5. `docs/reference/fastmcp-gateway.md` and the add-a-tool how-to corrected. `CHANGELOG.md` `[Unreleased]` entry added.

## Audit Provenance

- Severity: critical
- Source audits: `w1-gateway-mcp.md`
