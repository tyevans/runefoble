---
id: '0156'
title: Secret DM Spatial Traps, Map Switching and Stage Triggers
status: Complete
created: 2026-09-26
dependencies:
- TASK-0007
- TASK-0019
- TASK-0085
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0003
- PRD-0007
governing_stories:
- US-0018
target_release: 0.6.0
pr_url: https://github.com/tyevans/runefoble/pull/169
---
# TASK-0156: Secret DM Spatial Traps, Map Switching and Stage Triggers

## Status
Refined

## Summary
Implement DM-only hidden trap layers, proximity trigger cells, and multi-map switching with party token teleportation in `services/board_state/`, enforcing SpiceDB Zanzibar authorization so that secret markers remain invisible to players while firing automatic DM alerts upon movement breach.

## Problem Statement
Game Masters need the ability to lay secret traps, pit falls, and ambush trigger cells that stay completely invisible to player fog-of-war until triggered. Furthermore, moving between dungeon levels requires a seamless map-switch mechanism that teleports all player tokens in a single atomic transaction.

## Governing Architecture & ADRs
- **ADR-0001: Fine-Grained Authorization with SpiceDB Zanzibar**: DM-only layer visibility and trigger management permissions.
- **ADR-0006: Redis Streams Event Streaming**: Real-time trap sprung and map switch events.
- **ADR-0007: Domain-Driven Design Architecture**: Clean aggregate modeling for multi-layer battlemap grids.
- **ADR-0011: eventsource-py Core Event Sourcing**: Event-sourced `TrapPlaced`, `TrapSprung`, and `BattlemapSwitched` events.

## Product & User Story References
- **Product Requirement**: [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
- **User Story**: [`us-0018-secret-dm-traps-map-switching-and-stage-triggers.md`](../../user_stories/accepted/us-0018-secret-dm-traps-map-switching-and-stage-triggers.md)

## Detailed Specification & Implementation Plan
1. **Secret DM Grid Layer Schema (`services/board_state/src/board_state/traps/models.py`)**:
   - Schema for hidden cells, trigger types (step, proximity, touch), DC detection, and trap payload (< 130 lines).
2. **Trap Collision Evaluator (`services/board_state/src/board_state/traps/evaluator.py`)**:
   - Hook into token coordinate movement; detect breach of hidden trap cells, pause movement, and emit `board.trap.sprung` (< 150 lines).
3. **Map Switch & Party Teleportation (`services/board_state/src/board_state/traps/map_switcher.py`)**:
   - Atomic multi-token teleportation and battlemap asset switch handler (< 140 lines).
4. **CloudEvents Schema (`libs/runefoble_events/src/runefoble_events/board_traps.py`)**:
   - Define `TrapPlacedEvent`, `TrapSprungEvent`, `TrapDisarmedEvent`, and `BattlemapSwitchedEvent` (< 110 lines).
5. **REST API Router (`services/board_state/src/board_state/routers/traps.py`)**:
   - `POST /boards/{board_id}/traps`: Create secret trap (DM only).
   - `GET /boards/{board_id}/traps`: Retrieve traps (filtered by SpiceDB permission).
   - `POST /boards/{board_id}/switch-map`: Switch active map and teleport party tokens.

## INVEST Criteria Evaluation
- **Independent (I)**: Extends board state spatial capabilities without breaking 2D/3D token movement.
- **Negotiable (N)**: Trap trigger shapes and DC passive perception checks can be customized.
- **Valuable (V)**: Crucial for classic dungeon crawl exploration and dramatic DM surprises.
- **Estimable (E)**: Spatial bounding box checks and Zanzibar-secured endpoints.
- **Small (S)**: Bounded strictly to `services/board_state/src/board_state/traps/`; all files < 180 lines.
- **Testable (T)**: Frontdoor blackbox tests verify player exclusion from trap data and movement pause on trigger.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Zanzibar & Event Sourcing Alignment**:
   - Traps hidden layer strictly enforces `runefoble.zed` DM permissions.
   - All state transitions event-sourced via `eventsource-py`.
   - All modules strictly < 190 lines.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_traps/` validates that players cannot query secret traps, and token movement into trap cells triggers movement pause.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_traps/`, `uv run ruff check .`, and `uv run ruff format --check .`.
