---
id: '0671'
title: Encounter Round and Initiative Read Route for MCP query_encounter_state
status: Complete
created: 2026-11-17
dependencies:
- TASK-0603
governing_adrs:
- ADR-0007
- ADR-0011
- ADR-0014
governing_prds:
- PRD-0022
governing_stories:
- US-0008
- US-0035
target_release: 0.9.0
---

# TASK-0671: Encounter Round and Initiative Read Route for MCP query_encounter_state

## Status
Complete

## Summary
After TASK-0603, the MCP tool `query_encounter_state` reads board tokens from board_state. It no longer returns round or turn order, because no service route exposes them. This task exposes the combat round and initiative order from the owning bounded context and makes the MCP tool read it.

## Problem Statement
- TASK-0603 report: board_state has no encounter or initiative route. The canned round and initiative data were removed, so the tool returns less data than its contract says.
- Turn order and rounds belong to the game_session combat lifecycle (check `services/game_session` combat or turn routes first).

## Documentation & Architecture Review
- `docs/reference/fastmcp-gateway.md` documents the tool output. Update it.
- The gateway MCP stays thin: it calls the owning service over HTTP with the shared typed client.

## Product & User Story References
- PRD-0022, US-0008, US-0035: an AI agent reads the encounter state to plan an action.

## Detailed Specification & Implementation Plan
1. Find the owner of round and initiative state (game_session aggregate). If a read route exists, use it. If not, add `GET /api/v1/sessions/{session_id}/encounter` that returns round, active turn and the ordered initiative list from the aggregate.
2. `query_encounter_state` calls that route and merges the result with the board tokens. Upstream failure returns an MCP error result.
3. Register the route in OpenAPI. Update the reference docs.

## Frontdoor Blackbox Test Plan
- Start an encounter through public game_session routes. Advance one turn. The new GET route returns round 1 and the second combatant as active.
- MCP `query_encounter_state` (with stub HTTP upstreams at the process boundary) returns round and turn order.
- Upstream 503: the MCP tool returns an error result, not canned data.

## Definition of Done
- Tests above pass. Docs updated. CHANGELOG line given to the orchestrator.

## Audit Provenance

- Severity: medium
- Source audits: `w1-gateway-mcp.md`
