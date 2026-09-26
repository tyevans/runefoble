---
id: '0090'
title: Modular Routers Blackbox Test Suite Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0040
- TASK-0085
governing_adrs:
- ADR-0007
- ADR-0008
- ADR-0009
target_release: 0.2.0
---

# TASK-0090: Modular Routers Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_modular_routers.py` (411 lines, 82.2% of limit) into three specialized test suites (`tests/test_blackbox_watcher_routers.py`, `tests/test_blackbox_session_routers.py`, and `tests/test_blackbox_board_routers.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) and provide faster targeted test execution.

## Problem Statement
`tests/test_blackbox_modular_routers.py` currently stands at 411 lines—approaching the 500-line invariant ceiling. The test suite verifies public HTTP frontdoors, OpenAPI schemas, and route registrations across three distinct bounded contexts:
1. `services/the_watcher`: Transcribe-and-act, scene generation, encounter spawning, NPC turn, narration, and stand-in routes.
2. `services/game_session`: Session lifecycle, turns, presence, dice rolling, and WebSocket connection routes.
3. `services/board_state`: Spatial grid, movement validation, token positioning, and terrain hazards routes.

As new service routers and sub-endpoints are added, this test monolith will quickly breach 500 lines.

## Governing Architecture & ADRs
- **ADR-0007**: Development Tooling and Local Kind Cluster Workflows.
- **ADR-0008**: Property and Mutation Testing Strategy.
- **ADR-0009**: Code Quality and Linting with Ruff (strict file length invariant < 500 lines).

## Proposed Decomposition
1. **Watcher Modular Routers Suite (`tests/test_blackbox_watcher_routers.py`)**:
   - `test_watcher_openapi_routes_completeness`
   - `test_watcher_transcribe_and_act_frontdoor`
   - `test_watcher_scenes_generate_frontdoor`
   - `test_watcher_encounters_frontdoor`
   - `test_watcher_narrate_frontdoor`
   - `test_watcher_stand_in_frontdoor`
   - Target length: < 150 lines.
2. **Game Session Modular Routers Suite (`tests/test_blackbox_session_routers.py`)**:
   - `test_game_session_openapi_routes_completeness`
   - `test_game_session_lifecycle_frontdoor`
   - `test_game_session_turns_frontdoor`
   - `test_game_session_presence_frontdoor`
   - `test_game_session_dice_frontdoor`
   - Target length: < 140 lines.
3. **Board State Modular Routers Suite (`tests/test_blackbox_board_routers.py`)**:
   - `test_board_state_openapi_routes_completeness`
   - `test_board_state_spatial_frontdoor`
   - `test_board_state_tokens_frontdoor`
   - `test_board_state_terrain_frontdoor`
   - Target length: < 140 lines.
4. **Monolith Deletion**:
   - Remove `tests/test_blackbox_modular_routers.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Splits test layout across bounded context domains without modifying any service router implementation.
- **Negotiable (N)**: Split boundaries align naturally with bounded context borders.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and provides isolated test execution for individual bounded contexts.
- **Estimable (E)**: Pure pytest suite decomposition.
- **Small (S)**: Scope strictly isolated to `tests/test_blackbox_modular_routers.py`; all resulting files < 160 lines.
- **Testable (T)**: `uv run pytest tests/test_blackbox_*_routers.py` confirms 100% pass rate with zero regression.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Test Suite Creation**:
   - Dedicated test files created for Watcher, Game Session, and Board State modular routers.
   - Monolithic `tests/test_blackbox_modular_routers.py` deleted.
2. **Zero Coverage Regression**:
   - All 15 existing test cases preserved and passing with zero skips.
3. **File Length Compliance (Hard Invariant 6)**:
   - All resulting test files strictly under 180 lines.
4. **Frontdoor Test Execution**:
   - 100% pass rate on `uv run pytest tests/test_blackbox_watcher_routers.py tests/test_blackbox_session_routers.py tests/test_blackbox_board_routers.py`.
5. **Quality Gates**:
   - Passes `uv run ruff check tests/` and `uv run ruff format --check tests/`.
