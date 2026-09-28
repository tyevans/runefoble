---
id: '0339'
title: Initiative Tracker Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0022
governing_adrs:
- ADR-0006
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0002
governing_stories:
- US-0007
- US-0026
target_release: 0.8.0
---

# TASK-0339: Initiative Tracker Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_initiative_tracker.py` (285 lines, 57.0% of limit) into modular test submodules under `tests/test_blackbox_initiative_tracker/` (`test_encounter_lifecycle.py`, `test_turn_timer.py`, `test_manual_overrides.py`), ensuring all test modules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_initiative_tracker.py` verifies combat encounter initialization, initiative rolling, turn order rotation across rounds, turn timer countdowns, and manual DM initiative overrides in a single 285-line file. Approaching the 500-line invariant limit as new combat status effects and reaction turns are tested, it should be cleanly modularized.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/tutorials/02-running-your-first-session.md`: Interactive tabletop combat encounters and turn cycles.
  - `docs/how-to/manage-spoken-reactions-and-ready-actions.md`: Reaction turns and combat interrupts.
- **Governing Architecture & ADRs**:
  - **ADR-0006: Redis Streams Event Bus Architecture**: Combat turn advance events and initiative synchronization.
  - **ADR-0007: Domain-Driven Design Architecture**: Game session bounded context.
  - **ADR-0013: Modular Decomposition**: Single-responsibility test modules strictly < 150 lines.

## Scope of Work & Implementation Plan
1. **Combat Lifecycle Tests (`tests/test_blackbox_initiative_tracker/test_encounter_lifecycle.py`)**:
   - Extract encounter start, multi-player roll collection, sorted turn order, and round increment assertions (< 90 lines).
2. **Turn Timer Tests (`tests/test_blackbox_initiative_tracker/test_turn_timer.py`)**:
   - Extract turn countdown ticks, timeout auto-advancement, and timer reset events (< 90 lines).
3. **Manual Override Tests (`tests/test_blackbox_initiative_tracker/test_manual_overrides.py`)**:
   - Extract DM reordering, tie-breaker resolution, and delayed turn actions (< 90 lines).
4. **Verification**:
   - Safely remove monolithic `tests/test_blackbox_initiative_tracker.py` and verify all tests pass via `uv run pytest tests/test_blackbox_initiative_tracker/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Test modularization is isolated to the test directory and alters no production combat engine code.
- **Negotiable (N)**: Submodule file boundaries can be tailored cleanly.
- **Valuable (V)**: Protects combat encounter test suite from breaching Hard Invariant 6.
- **Estimable (E)**: Discrete test cases with existing 100% passing coverage.
- **Small (S)**: Each extracted test file will be strictly < 110 lines.
- **Testable (T)**: Directly executable via `uv run pytest tests/test_blackbox_initiative_tracker/`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_blackbox_initiative_tracker.py` decomposed into modular submodules under `tests/test_blackbox_initiative_tracker/`.
2. All extracted submodules strictly < 110 lines per Hard Invariant 6.
3. 100% of blackbox assertions pass via `uv run pytest tests/test_blackbox_initiative_tracker/`.
4. Monolithic `tests/test_blackbox_initiative_tracker.py` safely removed.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
