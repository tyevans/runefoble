# TASK-0007: Board Fog-of-War Spatial Visibility and Shroud Synchronization

## Status
Complete

## Summary
Integrated server-side spatial fog-of-war and Chebyshev visibility computation into `BoardAggregate` and the `board_state` service. Added `FogOfWarRevealed` event sourcing for token movements, party-wide visibility union calculations, and token filtering on `/api/v1/boards/{session_id}/visibility` so shrouded hostile tokens remain hidden from players while accessible to the DM.

## Key Changes
- `libs/runefoble_events/src/runefoble_events/events.py`:
  - Added `FogOfWarRevealed` domain event with `revealed_cells` and `revealed_by_token_id`.
- `services/board_state/src/board_state/aggregate.py`:
  - Added `vision_radius: int` to `PlacedTokenState`.
  - Added `fog_of_war_enabled` and `revealed_cells` to `BoardState`.
  - Implemented `calculate_chebyshev_cells` and `compute_party_visibility`.
  - Implemented automatic fog revelation upon token placement and movement.
  - Added `@handles(FogOfWarRevealed)` event handler.
- `services/board_state/src/board_state/main.py`:
  - Added `/api/v1/boards/{session_id}/visibility` endpoint.
  - Implemented role-based token visibility filtering (`is_dm` flag).
- `tests/test_board_state.py`:
  - Added unit tests for Chebyshev radius coverage, `revealed_cells` event sourcing, and API endpoint visibility filtering.

## Verification
- `uv run pytest`: 77/77 tests passed.
- `uv run ruff check .` & `uv run ruff format .`: Clean.
