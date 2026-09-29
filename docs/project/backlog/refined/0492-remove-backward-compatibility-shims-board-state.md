---
id: '0492'
title: Remove Backward Compatibility Shims & Re-exports in board_state
status: Refined
created: 2026-09-29
dependencies:
- TASK-0084
- TASK-0085
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0005
governing_stories:
- US-0005
- US-0027
target_release: 0.9.0
---

# TASK-0492: Remove Backward Compatibility Shims & Re-exports in board_state

## Status
Refined

## Summary
Decommission backward-compatibility router aggregator facades (`src/board_state/routers/previews.py`), frontend template aggregator facades (`ui/src/board-templates.ts`), and legacy re-export shims from `services/board_state`, migrating all Python and Lit Web Component callers directly to modular submodules.

## Problem Statement
In `services/board_state`:
- `src/board_state/routers/previews.py` acts as an aggregator facade re-exporting preview and kinematics endpoints.
- `ui/src/board-templates.ts` acts as an aggregator facade re-exporting modular Lit HTML templates across kinematics, cell, and overlays.
- `tests/test_board-templates.test.ts` actively tests re-export matching.
These aggregator facades exist solely for transitional backward compatibility, conflicting with the DoR zero-shim requirement.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`: Tactile token kinematics and preview overlays.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit component modularization.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Component architecture.
  - **ADR-0013: Frontend Microfrontend Architecture**: Clean isolation of microfrontend UI packages.

## Product & User Story References
- [`prd-0005-tactile-board-state-and-fog-of-war.md`](../../product/accepted/prd-0005-tactile-board-state-and-fog-of-war.md)
- [`us-0005-tactile-token-movement-and-snapping.md`](../../user_stories/accepted/us-0005-tactile-token-movement-and-snapping.md)
- [`us-0027-spoken-ghost-token-movement-previews.md`](../../user_stories/accepted/us-0027-spoken-ghost-token-movement-previews.md)

## Detailed Specification & Implementation Plan
1. **Decommission Router Aggregator Facade**:
   - In `services/board_state/src/board_state/routers/previews.py`, decompose or retire the facade; mount modular sub-routers directly in `routers/__init__.py` and `main.py`.
2. **Decommission UI Template Aggregator Facade**:
   - In `services/board_state/ui/src/board-templates.ts`, remove the facade re-export file.
   - Update `<runefoble-board>` and other UI consumers to import cell, kinematics, and overlay templates directly from `ui/src/templates/*`.
3. **Clean Up Tests**:
   - Update `frontend/test/board-templates.test.ts` to test template submodules directly, removing facade parity assertions.
4. **Audit Models and Helpers**:
   - Review `src/board_state/models.py` and `src/board_state/dependencies.py` to ensure only authoritative types and dependencies are exposed.

## INVEST Criteria Evaluation
- **Independent (I)**: Bounded cleanly to `services/board_state` backend and UI package.
- **Negotiable (N)**: Clean standard modular imports in TypeScript and Python.
- **Valuable (V)**: Removes transitional aggregator facades and simplifies template imports.
- **Estimable (E)**: Clearly identified router facade and UI template facade.
- **Small (S)**: Edits confined to a few files (< 100 lines total).
- **Testable (T)**: Verified via `uv run pytest tests/test_board_state*` and `pnpm test` in `services/board_state/ui`.

## Definition of Done
1. Router aggregator facade `src/board_state/routers/previews.py` retired.
2. UI template aggregator `ui/src/board-templates.ts` deleted and call sites migrated.
3. Obsolete facade parity tests removed.
4. Python and frontend typechecks/tests pass cleanly.
