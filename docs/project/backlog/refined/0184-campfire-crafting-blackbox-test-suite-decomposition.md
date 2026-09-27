---
id: '0184'
title: Campfire Crafting Blackbox Test Suite Modular Decomposition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0100
- TASK-0153
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0014
governing_stories:
- US-0044
target_release: 0.7.0
---

# TASK-0184: Campfire Crafting Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_campfire_crafting.py` (357 lines, 71.4% of limit) into modular test submodules under `tests/test_blackbox_campfire_crafting/` (`conftest.py`, `test_recipe_crafting.py`, `test_volatile_mishaps.py`, `test_campfire_boons.py`), keeping all test files strictly < 150 lines per Hard Invariant 6 and ADR-0003.

## Problem Statement
`tests/test_blackbox_campfire_crafting.py` tests alchemical recipe discovery, volatile mishap resolution tables, resting boons, and stronghold facility bonuses in a single 357-line file. Approaching the file size limit, it should be cleanly decomposed into focused submodules.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event emission and verification patterns.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
- **ADR-0011: PostgreSQL Event Store via eventsource-py**: Event-sourced aggregate state verification.

## Detailed Specification & Implementation Plan
1. **Shared Fixtures (`tests/test_blackbox_campfire_crafting/conftest.py`)**:
   - Extract test client, mock SpiceDB, and in-memory event bus/repository fixtures (< 70 lines).
2. **Recipe Crafting Tests (`tests/test_blackbox_campfire_crafting/test_recipe_crafting.py`)**:
   - Verify reagent combinations, recipe matching, and successful potion synthesis (< 110 lines).
3. **Volatile Mishap Tests (`tests/test_blackbox_campfire_crafting/test_volatile_mishaps.py`)**:
   - Verify failure thresholds, volatile explosion events, and setback conditions (< 110 lines).
4. **Campfire Boons Tests (`tests/test_blackbox_campfire_crafting/test_campfire_boons.py`)**:
   - Verify short/long rest recovery, camaraderie buff rolls, and facility bonuses (< 110 lines).
5. **Verification**:
   - Remove root test module `test_blackbox_campfire_crafting.py` and run `uv run pytest tests/test_blackbox_campfire_crafting/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Test refactoring isolated entirely to the campfire crafting test suite.
- **Negotiable (N)**: Test categories cleanly map to alchemical recipes, volatile mishaps, and resting boons.
- **Valuable (V)**: Safeguards against Hard Invariant 6 (500 lines) and improves readability of crafting tests.
- **Estimable (E)**: Deterministic extraction of test cases into discrete test modules.
- **Small (S)**: Bounded strictly to `tests/test_blackbox_campfire_crafting/`; all modules < 150 lines.
- **Testable (T)**: Frontdoor verification through pytest test suite execution against public endpoints and domain events.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `test_blackbox_campfire_crafting.py` removed; decomposed submodules created under `tests/test_blackbox_campfire_crafting/`.
   - All extracted test files strictly < 150 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest tests/test_blackbox_campfire_crafting/`.
3. **Quality Gates**:
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
