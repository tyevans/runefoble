---
id: 0238
title: GameSession Models Test Suite Modular Decomposition
status: Complete
created: 2026-09-27
dependencies:
- TASK-0178
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0009
- ADR-0010
- ADR-0011
- ADR-0013
governing_prds:
- PRD-0001
- PRD-0014
- PRD-0024
governing_stories:
- US-0023
- US-0044
- US-0073
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/377
---
# TASK-0238: GameSession Models Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_game_session_models_modular_decomposition.py` (339 lines, 67.8% of limit) into modular test sub-suites under `tests/test_game_session_models/` (`test_session_and_combat.py`, `test_reactions.py`, `test_settlements_and_facilities.py`, `test_autopilot_and_hotswap.py`), keeping all test modules strictly < 120 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_game_session_models_modular_decomposition.py` contains 339 lines verifying package exports, combat request/response validation, turn transition state mixins, reaction declarations, settlement charters, facility upgrades, and autopilot/hotswap payloads in a single test module. Approaching the file size threshold, decomposing it into focused sub-suites improves test organization and ensures compliance with Hard Invariant 6.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/define-event-sourced-aggregates.md`: Domain aggregate validation, declarative state transitions, and mixin testing.
  - `docs/how-to/manage-spoken-reactions-and-ready-actions.md`: Reaction triggers, ready-action contracts, and combat interrupts.
  - `docs/how-to/build-settlements-and-play-mobile-minigames.md`: Settlement charters, facility upgrades, and rest boon models.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular test package structure.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation across game session aggregates, reactions, settlements, and AI pilot models.
  - **ADR-0009: Code Quality and Linting with Ruff and Pre-commit**: Strict linting, formatting, and type checks.
  - **ADR-0010: Continuous Integration Pipeline**: Rapid and modular test suite execution.
  - **ADR-0011: eventsource-py Core Event Sourcing**: Verification of state transitions and model invariants.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Modular isolation across bounded contexts.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
  - [`prd-0014-downtime-crafting-and-stronghold-engine.md`](../../product/accepted/prd-0014-downtime-crafting-and-stronghold-engine.md)
  - [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
  - [`us-0023-spoken-reaction-interrupts-and-ready-actions.md`](../../user_stories/accepted/us-0023-spoken-reaction-interrupts-and-ready-actions.md)
  - [`us-0044-party-stronghold-facilities-and-crafting.md`](../../user_stories/accepted/us-0044-party-stronghold-facilities-and-crafting.md)
  - [`us-0073-customizable-establishments-and-assignable-npc-workers.md`](../../user_stories/accepted/us-0073-customizable-establishments-and-assignable-npc-workers.md)

## Detailed Specification & Implementation Plan
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

## INVEST Criteria Evaluation
- **Independent (I)**: Test refactoring executes independently of API route changes.
- **Negotiable (N)**: Submodule groupings can be fine-tuned while keeping all files < 120 lines.
- **Valuable (V)**: Prevents test suite file size bloat and ensures clear segregation of domain models.
- **Estimable (E)**: Straightforward extraction of existing assertions.
- **Small (S)**: Each extracted test file strictly < 120 lines.
- **Testable (T)**: Frontdoor test execution via `uv run pytest tests/test_game_session_models/`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_game_session_models_modular_decomposition.py` replaced by modular sub-suites under `tests/test_game_session_models/`.
2. All test files strictly < 120 lines each per Hard Invariant 6.
3. Passes `uv run pytest tests/test_game_session_models/` with 100% test pass rate.
4. Passes `uv run ruff check .` and `uv run ruff format --check .`.
