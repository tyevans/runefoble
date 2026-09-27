---
id: '0216'
title: Faction Turf War Test Suite Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0162
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0017
governing_stories:
- US-0057
- US-0019
target_release: 0.7.0
---

# TASK-0216: Faction Turf War Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_turf_war/test_blackbox_turf_war.py` (375 lines, 75.0% of limit) into modular test submodules under `tests/test_blackbox_turf_war/` (`conftest.py`, `test_skirmishes.py`, `test_unrest_escalation.py`, `test_turf_war_api.py`), keeping all test files strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_turf_war/test_blackbox_turf_war.py` was introduced in TASK-0162 and covers skirmish simulations, territory capture, unrest calculations, and REST API endpoints in a single monolithic test file of 375 lines. As additional multi-party faction clash scenarios and espionage mechanics are added, this suite will breach the 500-line hard ceiling unless decomposed into focused, single-responsibility test files.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Verifies reactive gameplay pipelines and unrest progression.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event emission and verification patterns.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
- **ADR-0011: PostgreSQL Event Store via eventsource-py**: Event-sourced aggregate state verification.

## Scope of Work
1. **Shared Test Fixtures (`tests/test_blackbox_turf_war/conftest.py`)**:
   - Extract test client setup, mock SpiceDB, mock Redis Streams bus, in-memory event store, and repository helpers (< 70 lines).
2. **Faction Skirmishes Tests (`tests/test_blackbox_turf_war/test_skirmishes.py`)**:
   - Test skirmish initiation, tactical modifiers, casualties, and outcome resolution (< 100 lines).
3. **Unrest Escalation Tests (`tests/test_blackbox_turf_war/test_unrest_escalation.py`)**:
   - Test regional unrest threshold triggers, riot states, and event publication (< 100 lines).
4. **Turf War API Tests (`tests/test_blackbox_turf_war/test_turf_war_api.py`)**:
   - Test REST endpoints for active disputes, territory state queries, and conflict initiation (< 110 lines).
5. **Verification**:
   - Remove root test module `test_blackbox_turf_war.py` and run `uv run pytest tests/test_blackbox_turf_war/`.

## Definition of Done
- `tests/test_blackbox_turf_war/` package decomposed with all files strictly < 150 lines.
- Zero files in test suite exceed 200 lines.
- All tests pass via `uv run pytest tests/test_blackbox_turf_war/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
