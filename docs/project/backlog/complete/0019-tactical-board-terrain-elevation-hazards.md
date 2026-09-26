---
id: 0019
title: Tactical Board Terrain Elevation, Difficult Terrain & Hazard Grid
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0004, TASK-0007]
governing_adrs: [ADR-0007, ADR-0011]
target_release: 0.1.0
---

# TASK-0019: Tactical Board Terrain Elevation, Difficult Terrain & Hazard Grid

## Status
Complete

## Summary
Implemented tactical cell elevation levels, difficult terrain movement cost multipliers (2x budget cost per cell traversed), and environmental hazard triggers (dispatching `TokenHazardTriggered` events with hazard damage dice) in `board_state` (US-0012, PRD-0003). Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup), test verification was authored first in `tests/test_blackbox_board_terrain.py`, strictly creating boards via `POST /api/v1/boards`, placing tokens via `POST /api/v1/boards/{id}/tokens`, configuring terrain via `POST /api/v1/boards/{id}/terrain`, and issuing moves via `POST /api/v1/boards/{id}/tokens/{token_id}/move`, asserting on Chebyshev distance costs, lava hazards (`2d10`), and board state query projections without backdoor internal state tampering.

## Key Changes
- `libs/runefoble_events/src/runefoble_events/events.py` & `__init__.py`:
  - Added `TerrainCellModified` domain event (`runefoble.events.board.terrain_modified`) capturing cell elevation, terrain type, and hazards.
  - Added `TokenHazardTriggered` domain event (`runefoble.events.board.hazard_triggered`) capturing token ID, hazard type, and damage dice.
- `services/board_state/src/board_state/aggregate.py`:
  - Added `TerrainCellState` model and `TerrainDict` dictionary supporting string `"x,y"` and tuple `(x, y)` keys.
  - Added `terrain_cells` and `active_hazards` to `BoardState`.
  - Added `active_hazard` and `hazard_status` to `PlacedTokenState`.
  - Implemented `configure_terrain`, `get_terrain`, `calculate_movement_path`, and `calculate_movement_cost` (2x cost per cell for difficult terrain).
  - Updated `move_token` to validate movement budget, emit `TokenHazardTriggered` events when traversing hazards, and update token hazard status.
  - Added `@handles(TerrainCellModified)` and `@handles(TokenHazardTriggered)` event handlers.
- `services/board_state/src/board_state/main.py`:
  - Added `POST /api/v1/boards` endpoint to create clean tactical grids with specified dimensions.
  - Added `POST /api/v1/boards/{id}/terrain` endpoint to configure cell terrain, elevation, and hazards.
  - Added `POST /api/v1/boards/{id}/tokens/{token_id}/move` endpoint returning movement costs and hazard triggers.
  - Updated `GET /api/v1/boards/{id}` to project terrain grid and active hazards.
- `docs/reference/events-schema.md`:
  - Documented `TerrainCellModified` and `TokenHazardTriggered` in the Diataxis reference documentation.
- `docs/project/product/accepted/prd-0003-spatial-fog-of-war-and-visibility-engine.md`:
  - Updated checkable outcomes to include terrain elevation, difficult terrain movement budget penalties, and hazard events.

## Verification
- `uv run pytest tests/test_blackbox_board_terrain.py`: 3/3 passed.
- `uv run pytest`: 151/151 passed across all services and libraries.
- `uv run ruff check .`: Clean (all checks passed).
- File length limits: All files under 500 lines.
