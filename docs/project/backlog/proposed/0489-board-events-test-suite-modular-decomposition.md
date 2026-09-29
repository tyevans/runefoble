---
id: '0489'
title: Board Events Test Suite Modular Decomposition
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0231
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0003
- PRD-0005
- PRD-0013
governing_stories:
- US-0014
- US-0043
target_release: 0.9.0
---

# TASK-0489: Board Events Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose the monolithic board events test suite (`tests/test_board_events.py`, 431 lines) into focused, single-responsibility test modules under `tests/board_events/` (`test_token_events.py`, `test_terrain_and_fog_events.py`, `test_spells_and_physics_events.py`), ensuring all test files remain comfortably under 200 lines and preserve 100% test coverage per Rule 6 (<500 lines) and ADR-0014.

## Problem Statement
Following the modularization of board domain events in TASK-0231, the accompanying test suite `tests/test_board_events.py` stands at 431 lines. Per AGENTS.md Rule 6, source and test files exceeding 400 lines represent refactoring candidates approaching the hard 500-line invariant. As future board event schemas and validations expand, this monolithic test file risks breaching the hard line limit.

## Governing Architecture & ADRs
- **ADR-0003: Continuous Architecture & Modular Refactoring**: Proactive decomposition of test modules approaching line limits.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Validating CloudEvents serialization and event payloads.
- **ADR-0007: Domain-Driven Design Architecture**: Aligning test organization with bounded context event categories.
- **ADR-0014: Behavior-Driven Development (BDD) and Frontdoor Blackbox Testing Governance**: Modular test execution through public event models.

## Product & User Story References
- [`prd-0003-spatial-fog-of-war-and-visibility-engine.md`](../../product/accepted/prd-0003-spatial-fog-of-war-and-visibility-engine.md)
- [`prd-0005-realtime-websocket-board-sync.md`](../../product/accepted/prd-0005-realtime-websocket-board-sync.md)
- [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
- [`us-0014-tactile-board-fog-of-war.md`](../../user_stories/accepted/us-0014-tactile-board-fog-of-war.md)
- [`us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md`](../../user_stories/accepted/us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md)

## Scope of Work
1. **Decompose `tests/test_board_events.py`**:
   - Create package directory `tests/board_events/` with `__init__.py`.
   - Extract token lifecycle and movement tests into `tests/board_events/test_token_events.py` (< 150 lines).
   - Extract terrain, elevation, and fog-of-war visibility tests into `tests/board_events/test_terrain_and_fog_events.py` (< 150 lines).
   - Extract spell template, lighting, and 3D collision event tests into `tests/board_events/test_spells_and_physics_events.py` (< 150 lines).
2. **Backward Compatibility**:
   - Provide a shim in `tests/test_board_events.py` or remove and update any test runner references so `pytest tests/test_board_events.py` continues to execute seamlessly.
3. **Verification**:
   - Ensure all decomposed test suites pass with 100% assertions and no line count exceeds 200 lines.

## Definition of Done
1. `tests/test_board_events.py` decomposed into modular files under `tests/board_events/`.
2. Every new test module is strictly under 250 lines.
3. Full test suite passes: `uv run pytest tests/board_events/`.
4. Code passes `uv run ruff check tests/board_events/`.
