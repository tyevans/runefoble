---
id: '0070'
title: Missing Player AI Stand-In and Absentee Recap Test Suite Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0003, TASK-0011]
governing_adrs: [ADR-0003, ADR-0006]
target_release: 0.2.0
---

# TASK-0070: Missing Player AI Stand-In and Absentee Recap Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_stand_in_engine.py` (343 lines, 68.6% of limit) into two focused test modules (`tests/test_stand_in_tactics_unit.py` and `tests/test_blackbox_stand_in_service.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as stand-in policy guardrails and mid-session hot-swap handoffs (TASK-0055) are introduced.

## Problem Statement
`tests/test_stand_in_engine.py` currently spans 343 lines and conjoins two distinct test paradigms across two separate microservices:
1. Pure unit tests for `TheWatcherEngine` stand-in action generation, penalty mechanics (`drunk`, `foolishness`, `cowardice`, `greed`), and personality traits (`scholarly`, `valiant`, `impulsive`).
2. Blackbox HTTP API integration tests against `services/the_watcher` (`POST /api/v1/watcher/stand-in/act`) and `services/game_session` (`POST /api/v1/sessions/{id}/absent-penalties` and `/api/v1/sessions/{id}/recap`), verifying Redis Streams event publishing (`StandInActionDecided`, `AbsencePenaltyApplied`).

As upcoming Milestone 3 tasks add stand-in policy guardrails (TASK-0055) and DM co-pilot whispers (TASK-0053), this test suite will rapidly breach the 500-line ceiling unless partitioned by test layer and bounded context.

## Proposed Decomposition
1. **Stand-In Tactics & Personality Unit Suite (`tests/test_stand_in_tactics_unit.py`)**:
   - Unit tests for penalty modifiers (dice roll formula adjustments, slurred dialogue, defensive positioning, and distraction effects).
   - Personality trait flavor integration with combined penalty conditions (< 150 lines).
2. **Blackbox Stand-In & Recap Service Suite (`tests/test_blackbox_stand_in_service.py`)**:
   - ASGI client tests for The Watcher stand-in action endpoint and Redis Streams event emission.
   - ASGI client tests for Game Session penalty application and absentee chronicle recap generation (< 200 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors test suite organization without changing production stand-in engine or session recap code.
- **Negotiable (N)**: Test fixture sharing structure can be tuned.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and improves test clarity between unit logic and HTTP integration.
- **Estimable (E)**: Standard test suite partitioning into unit and blackbox integration layers.
- **Small (S)**: Scope strictly isolated to `tests/test_stand_in_engine.py`; all resulting files < 200 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_stand_in_*.py tests/test_blackbox_stand_in_*.py`.

## Acceptance Criteria
1. `tests/test_stand_in_engine.py` decomposed into modular test files strictly under 220 lines each.
2. 100% test pass rate on all existing stand-in and recap test cases.
3. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
4. Maintains blackbox frontdoor interactions via public HTTP endpoints and Redis Streams domain events.
