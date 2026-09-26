---
id: 0019
title: Tactical Board Terrain Elevation, Difficult Terrain & Hazard Grid
status: Refined
created: 2026-09-25
dependencies: [TASK-0004, TASK-0007]
governing_adrs: [ADR-0007, ADR-0011]
target_release: 0.1.0
---

# TASK-0019 — Tactical Board Terrain Elevation, Difficult Terrain & Hazard Grid

## Summary
Implement tactical cell elevation levels, difficult terrain movement cost multipliers, and environmental hazard triggers in `board_state` (US-0012, PRD-0001). Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup), test verification must strictly create boards, configure terrain cells, and issue token moves through the public HTTP frontdoors (`POST /api/v1/boards/...`), asserting on Chebyshev distance penalties and hazard damage events without backdoor internal state tampering.

## Scope & Changes
1. **Domain Events (`libs/runefoble_events/events.py`)**:
   - `TerrainCellModified`: `session_id`, `board_id`, `x`, `y`, `elevation`, `terrain_type`, `hazard`. (@register_event("runefoble.events.board.terrain_modified"))
   - `TokenHazardTriggered`: `session_id`, `board_id`, `token_id`, `hazard_type`, `damage_dice`. (@register_event("runefoble.events.board.hazard_triggered"))
2. **Aggregate Extension (`services/board_state/src/board_state/aggregate.py`)**:
   - Add terrain map tracking elevation, difficult terrain, and hazards to `BoardAggregate`.
   - Update movement validation to calculate movement speed penalties across difficult terrain and trigger hazards.
3. **Public Frontdoor Endpoints (`services/board_state/src/board_state/main.py`)**:
   - `POST /api/v1/boards/{id}/terrain`
   - `POST /api/v1/boards/{id}/tokens/{token_id}/move`
   - `GET /api/v1/boards/{id}`
4. **Blackbox TDD Suite (`tests/test_blackbox_board_terrain.py`)**:
   - Author blackbox test first using `TestClient(app)`.
   - Setup strictly via frontdoor `POST /api/v1/boards` and `POST /api/v1/boards/{id}/tokens`.
   - Apply terrain via frontdoor and verify token movement and hazard triggers.
