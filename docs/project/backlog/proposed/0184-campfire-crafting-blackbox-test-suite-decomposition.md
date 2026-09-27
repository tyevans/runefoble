---
id: '0184'
title: Campfire Crafting Blackbox Test Suite Modular Decomposition
status: Proposed
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
Proposed

## Summary
Decompose `tests/test_blackbox_campfire_crafting.py` (357 lines, 71.4% of limit) into modular test submodules under `tests/test_blackbox_campfire_crafting/` (`conftest.py`, `test_recipe_crafting.py`, `test_volatile_mishaps.py`, `test_campfire_boons.py`), keeping all test files strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_campfire_crafting.py` tests alchemical recipe discovery, volatile mishap resolution tables, resting boons, and stronghold facility bonuses in a single 357-line file. Approaching the file size limit, it should be cleanly decomposed into focused submodules.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event emission and verification patterns.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
- **ADR-0011: PostgreSQL Event Store via eventsource-py**: Event-sourced aggregate state verification.

## Scope of Work
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

## Definition of Done
- `tests/test_blackbox_campfire_crafting/` package created with all files strictly < 150 lines.
- Zero files in test suite exceed 200 lines.
- All tests pass via `uv run pytest tests/test_blackbox_campfire_crafting/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
