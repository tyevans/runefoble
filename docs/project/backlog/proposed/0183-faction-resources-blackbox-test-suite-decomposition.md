---
id: '0183'
title: Faction Resources Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0161
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0017
governing_stories:
- US-0057
target_release: 0.7.0
---

# TASK-0183: Faction Resources Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_faction_resources/test_blackbox_faction_resources.py` (360 lines, 72.0% of limit) into modular test submodules under `tests/test_blackbox_faction_resources/` (`conftest.py`, `test_resource_operations.py`, `test_mercenary_recruitment.py`, `test_bribery_mechanics.py`), keeping all test files strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_faction_resources/test_blackbox_faction_resources.py` was introduced in TASK-0161 and covers resource transactions, mercenary hiring, bribery checks, and Redis event emissions in a single monolithic test file of 360 lines. As additional faction turf war and regional unrest tests are added, this suite will breach the 500-line limit unless decomposed into focused, single-responsibility test files.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event emission and verification patterns.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
- **ADR-0011: PostgreSQL Event Store via eventsource-py**: Event-sourced aggregate state verification.

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_faction_resources/conftest.py`)**:
   - Extract test client, mock SpiceDB, in-memory event bus/store fixtures, and aggregate repository setup (< 70 lines).
2. **Resource Operations Tests (`tests/test_blackbox_faction_resources/test_resource_operations.py`)**:
   - Test treasury deposit, resource depletion, and capacity bounds (< 100 lines).
3. **Mercenary Recruitment Tests (`tests/test_blackbox_faction_resources/test_mercenary_recruitment.py`)**:
   - Test mercenary recruitment costs, unit tiers, and upkeep deduction (< 100 lines).
4. **Bribery Mechanics Tests (`tests/test_blackbox_faction_resources/test_bribery_mechanics.py`)**:
   - Test bribery attempt resolution, success/failure thresholds, and event emission (< 110 lines).
5. **Verification**:
   - Remove root test module `test_blackbox_faction_resources.py` and run `uv run pytest tests/test_blackbox_faction_resources/`.

## Definition of Done
- `tests/test_blackbox_faction_resources/` package decomposed with all files strictly < 150 lines.
- Zero files in test suite exceed 200 lines.
- All tests pass via `uv run pytest tests/test_blackbox_faction_resources/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
