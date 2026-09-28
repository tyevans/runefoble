---
id: '0238'
title: GameSession Models Test Suite Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0178
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0001
- PRD-0014
governing_stories:
- US-0023
- US-0044
target_release: 0.8.0
---

# TASK-0238: GameSession Models Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_game_session_models_modular_decomposition.py` (340 lines, 68.0% of limit) into modular test sub-suites under `tests/test_game_session_models/` (`test_session_and_combat.py`, `test_reactions.py`, `test_settlements_and_facilities.py`, `test_autopilot_and_hotswap.py`), keeping all test modules strictly < 120 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_game_session_models_modular_decomposition.py` contains 340 lines verifying package exports, combat request/response validation, turn transition state mixins, reaction declarations, settlement charters, facility upgrades, and autopilot/hotswap payloads in a single test module. Approaching the file size threshold, decomposing it into focused sub-suites improves test organization and ensures compliance with Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular test package structure.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation across game session aggregates, reactions, settlements, and AI pilot models.
- **ADR-0011: eventsource-py Core Event Sourcing**: Verification of state transitions and model invariants.

## Scope of Work
1. **Shared Fixtures (`tests/test_game_session_models/conftest.py`)**:
   - Extract mock session payloads, UUID generators, and participant state fixtures (< 50 lines).
2. **Session & Combat Tests (`tests/test_game_session_models/test_session_and_combat.py`)**:
   - Test session creation, joining, turn progression, and combat transition mixins (< 90 lines).
3. **Reactions Tests (`tests/test_game_session_models/test_reactions.py`)**:
   - Test reaction declarations, triggers evaluation, ready actions, and resolution models (< 90 lines).
4. **Settlements & Facilities Tests (`tests/test_game_session_models/test_settlements_and_facilities.py`)**:
   - Test settlement charters, facility tiers, upgrades, and rest boon models (< 90 lines).
5. **Autopilot & Hot-Swap Tests (`tests/test_game_session_models/test_autopilot_and_hotswap.py`)**:
   - Test AI stand-in takeover, absentee autopilot, and mid-session hot-swap models (< 90 lines).
6. **Verification**:
   - Run `uv run pytest tests/test_game_session_models/` and ensure 100% pass rate.

## Definition of Done
- `tests/test_game_session_models_modular_decomposition.py` replaced by modular sub-suites under `tests/test_game_session_models/`.
- All test files strictly < 120 lines each.
- Passes `uv run pytest tests/test_game_session_models/`.
- Passes `uv run ruff check .` and `uv run ruff format --check .`.
