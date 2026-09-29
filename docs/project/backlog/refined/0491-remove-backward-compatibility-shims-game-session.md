---
id: '0491'
title: Remove Backward Compatibility Shims & Re-exports in game_session
status: Refined
created: 2026-09-29
dependencies:
- TASK-0238
- TASK-0273
- TASK-0278
- TASK-0279
- TASK-0280
- TASK-0282
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0011
- ADR-0013
governing_prds:
- PRD-0004
- PRD-0008
- PRD-0012
governing_stories:
- US-0004
- US-0021
- US-0044
target_release: 0.9.0
---

# TASK-0491: Remove Backward Compatibility Shims & Re-exports in game_session

## Status
Refined

## Summary
Purge all backward-compatibility facades, router shims, and legacy field aliases from `services/game_session` (`aggregate.py`, `combat_routes.py`, `caravan.py`, `caravan_ledger.py`, `settlements/aggregate.py`, `routers/caravan_contracts.py`, `settlement/auth.py`, `settlement/workers.py`, `settlement/haggling.py`, and `worker_models.py` aliases), migrate callers directly to authoritative submodules, and delete facade parity tests.

## Problem Statement
`services/game_session` has undergone extensive domain modularization (extracting settlements, caravan contracts, combat encounters, and haggling). However, at each step, backward-compatibility facade files were retained:
- `game_session/aggregate.py` (facade re-exporting `GameSessionAggregate`)
- `game_session/combat_routes.py` (compatibility shim for `routers/combat.py`)
- `game_session/caravan.py` and `caravan_ledger.py` (compatibility facades)
- `game_session/settlements/aggregate.py` (facade)
- `game_session/routers/caravan_contracts.py` (facade)
- `game_session/settlement/auth.py`, `workers.py`, `haggling.py` (aggregator facades)
- `worker_models.py` field aliases (`alias="stock"`, `alias="price_gp"`)
- Tests in `tests/test_game_session_modular_decomposition.py` and `tests/test_game_session_projections.py` asserting facade parity.
These artifacts contradict the DoR zero backward compatibility mandate and must be removed.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/coordinate-game-session-lobby-and-readiness.md`: Session lifecycle and coordination.
  - `docs/how-to/run-tavern-minigames-and-merchant-haggling.md`: Haggling and minigames domain.
- **Governing Architecture & ADRs**:
  - **ADR-0006: Redis Streams Event Bus**: Session event publishing.
  - **ADR-0011: eventsource-py Core Event Sourcing**: Aggregates and command handlers.
  - **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend component separation.

## Product & User Story References
- [`prd-0004-realtime-game-session-orchestration.md`](../../product/accepted/prd-0004-realtime-game-session-orchestration.md)
- [`prd-0012-frontier-settlements-and-havens.md`](../../product/accepted/prd-0012-frontier-settlements-and-havens.md)
- [`us-0004-session-lobby-and-player-readiness.md`](../../user_stories/accepted/us-0004-session-lobby-and-player-readiness.md)
- [`us-0044-charter-frontier-settlement-haven.md`](../../user_stories/accepted/us-0044-charter-frontier-settlement-haven.md)

## Detailed Specification & Implementation Plan
1. **Delete Facade and Compatibility Shim Files**:
   - Delete `services/game_session/src/game_session/aggregate.py`.
   - Delete `services/game_session/src/game_session/combat_routes.py`.
   - Delete `services/game_session/src/game_session/caravan.py`.
   - Delete `services/game_session/src/game_session/caravan_ledger.py`.
   - Delete `services/game_session/src/game_session/settlements/aggregate.py`.
   - Delete `services/game_session/src/game_session/routers/caravan_contracts.py`.
   - Delete `services/game_session/src/game_session/settlement/auth.py`.
   - Delete `services/game_session/src/game_session/settlement/workers.py`.
   - Delete `services/game_session/src/game_session/settlement/haggling.py`.
2. **Remove Model Field Aliases**:
   - In `services/game_session/src/game_session/settlement/worker_models.py`, remove legacy aliases (`alias="stock"`, `alias="price_gp"`), standardizing on canonical field names.
3. **Migrate Import Sites Across Workspace**:
   - Update `game_session/main.py`, router mounts, and cross-package consumers to import directly from modular submodules (`game_session.aggregate.*`, `game_session.caravan.*`, `game_session.settlement.*`).
4. **Update Blackbox Test Suites**:
   - In `tests/test_game_session_modular_decomposition.py`, delete `test_package_facade_and_backward_compatibility()`.
   - In `tests/test_game_session_projections.py`, remove facade re-export tests.
   - Ensure all blackbox tests pass against direct modular imports.

## INVEST Criteria Evaluation
- **Independent (I)**: Self-contained within `services/game_session`.
- **Negotiable (N)**: Clean modular organization following standard package structures.
- **Valuable (V)**: Eliminates 9 legacy shim files and cleans up the largest bounded context.
- **Estimable (E)**: Precise list of files to delete and test methods to prune.
- **Small (S)**: File deletions and import updates adhering to the < 500 lines invariant.
- **Testable (T)**: Verified by `uv run pytest tests/test_game_session* tests/test_blackbox_session*`.

## Definition of Done
1. All 9 facade and shim files deleted from `services/game_session`.
2. Model field aliases removed in favor of canonical naming.
3. Internal routers and external tests updated to direct modular imports.
4. Obsolete facade parity tests removed.
5. All game session tests pass with zero warnings.
