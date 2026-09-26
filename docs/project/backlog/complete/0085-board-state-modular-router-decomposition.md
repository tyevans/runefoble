---
id: 0085
title: Board State API Router and Spatial Handler Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0007
- TASK-0019
- TASK-0040
- TASK-0084
governing_adrs:
- ADR-0003
- ADR-0009
- ADR-0011
- ADR-0013
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/51
governing_prds:
- PRD-0003
governing_stories:
- US-0012
---
# TASK-0085: Board State API Router and Spatial Handler Modular Decomposition

## Status
Refined

## Summary
Decompose `services/board_state/src/board_state/main.py` (426 lines, 85.2% of limit) into modular FastAPI routers (`routers/boards.py`, `routers/tokens.py`, `routers/terrain.py`, `routers/previews.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) and align with the modular router architecture established in ADR-0003 and TASK-0040.

## Problem Statement
Health scans identify `services/board_state/src/board_state/main.py` at 426 lines. The file currently bundles:
1. Application lifecycle, FastAPI bootstrap, and microfrontend `/ui/manifest` discovery endpoint.
2. Board aggregate CRUD endpoints (`POST /api/v1/boards`, `GET /api/v1/boards/{board_id}`).
3. Token placement, coordinate translation, and removal (`/tokens`).
4. Terrain elevation, hazard grid mutations, and fog-of-war spatial visibility queries (`/terrain`, `/fog-of-war/reveal`, `/fog-of-war/shroud`).
5. Kinematic movement preview endpoints and WebSocket live preview streaming (`/preview-move`, `/ws/boards/{board_id}`).

As tactical board kinematics and multi-level combat terrain rules expand, this file will exceed 500 lines without modular router decomposition.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace for Python Bounded Contexts.
- **ADR-0009**: Code Quality and Linting with Ruff (file length limit < 500 lines).
- **ADR-0011**: eventsource-py Core Event Sourcing Architecture.
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring (`/ui/manifest`).

## Proposed Decomposition
1. **Board Management Router (`services/board_state/src/board_state/routers/boards.py`)**:
   - Board aggregate initialization, board retrieval, and `/ui/manifest` (~80 lines).
2. **Tokens Router (`services/board_state/src/board_state/routers/tokens.py`)**:
   - Token placement, coordinate relocation, and token removal endpoints (~100 lines).
3. **Terrain & Visibility Router (`services/board_state/src/board_state/routers/terrain.py`)**:
   - Hazard grid definitions, elevation levels, and fog-of-war shroud/reveal endpoints (~110 lines).
4. **Kinematics & Preview Router (`services/board_state/src/board_state/routers/previews.py`)**:
   - Kinematic route calculation (`/preview-move`) and WebSocket streaming connection (`/ws/boards/{board_id}`) (~110 lines).
5. **Main Service Orchestration Shell (`services/board_state/src/board_state/main.py`)**:
   - Lightweight FastAPI initialization mounting sub-routers (< 90 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Internal router restructuring within `services/board_state`; no changes to external HTTP contracts, WebSocket message schemas, or CloudEvents.
- **Negotiable (N)**: Distribution of endpoints across router modules can be adjusted.
- **Valuable (V)**: Protects Hard Invariant 6 (< 500 lines) and improves modular testability and maintenance.
- **Estimable (E)**: Follows identical pattern established in `services/the_watcher` and `services/game_session` during TASK-0040.
- **Small (S)**: Scope strictly isolated to `services/board_state/src/board_state/`; all resulting files < 150 lines.
- **Testable (T)**: Existing blackbox tests (`tests/test_board_state.py`, `tests/test_tactile_board_kinematics.py`, `tests/test_blackbox_board_fog_of_war.py`) verify 100% behavior preservation.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Router Extraction**:
   - `services/board_state/src/board_state/main.py` decomposed into `routers/boards.py`, `routers/tokens.py`, `routers/terrain.py`, and `routers/previews.py`.
2. **File Length Compliance (Hard Invariant 6)**:
   - All modified and newly created source files strictly under 200 lines.
3. **Frontdoor Blackbox Verification**:
   - 100% test pass on `uv run pytest tests/test_board_state.py tests/test_tactile_board_kinematics.py tests/test_blackbox_board_fog_of_war.py tests/test_microfrontends.py`.
4. **Public Contract Integrity**:
   - Zero changes to public HTTP status codes, routes, or WebSocket payloads.
5. **Static Analysis & Linting**:
   - Passes `uv run ruff check services/board_state` and `uv run ruff format --check services/board_state`.
