---
id: '0885'
title: MCP create_encounter Makes One Owner Call
status: Complete
created: 2026-11-19
dependencies:
- TASK-0749
governing_adrs:
- ADR-0007
- ADR-0015
governing_prds:
- PRD-0001
governing_stories:
- US-0031
target_release: 0.9.0
---

# TASK-0885: MCP create_encounter Makes One Owner Call

## Status
Complete

Remaining part of TASK-0749 (`.audit/work/0749.md`). Read the decision in `docs/project/backlog/complete/0749-*.md`.

## Summary
game_session now has `POST /api/v1/sessions/{session_id}/encounters/start` (TASK-0749). It starts combat and records the placements on one event, and board_state places the tokens from that event. The MCP `create_encounter` tool still starts combat, creates the board and places each token itself. Make it read monster CR from rules_compendium, then make one write call to the new owner route. Delete `_fetch_or_create_board`, the grid constants and the placement loop from the gateway.

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)

## Detailed Specification & Implementation Plan
1. Add the owner route to `runefoble_platform.service_client.owner_routes`.
2. Rewrite `create_encounter` as: CR reads, then one call to the owner route with the caller token. Map the owner errors the same way as the other MCP tools.
3. Remove the gateway placement code and its tests; update `docs/reference/fastmcp-gateway.md`.

## Frontdoor Test Plan
Through the MCP HTTP frontdoor with live loopback owners: the tool answers with the started combat; after the board consumer runs, the board read shows every token; a player gets the owner 403; an unknown monster gets the compendium 404 and starts nothing.

## INVEST Criteria Evaluation
Small. Testable through the MCP frontdoor.

## Definition of Done
1. Tests pass. 2. No placement code in gateway/mcp. 3. `make health-check` passes.
