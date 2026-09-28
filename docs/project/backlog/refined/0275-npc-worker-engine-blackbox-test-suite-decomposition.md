---
id: '0275'
title: NPC Worker Engine Blackbox Test Suite Modular Decomposition
status: Refined
created: 2026-09-28
dependencies:
- TASK-0260
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0007
- ADR-0008
- ADR-0010
governing_prds:
- PRD-0024
governing_stories:
- US-0073
target_release: 0.8.0
---

# TASK-0275: NPC Worker Engine Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_npc_worker_engine.py` (376 lines, 75.2% of limit) into modular test sub-suites under `tests/test_blackbox_npc_worker/` (`conftest.py`, `test_worker_assignment.py`, `test_morale_and_wages.py`, `test_social_graph.py`), ensuring all test sub-modules remain strictly < 130 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_npc_worker_engine.py` has grown to 376 lines in its initial implementation, testing worker generation, establishment assignments, wage payouts, morale calculation, relationship link mutations, and event publishing over Redis streams within a single module. As additional worker traits, grievance events, and strike states are introduced, this suite will approach the 500-line invariant limit unless decoupled into focused submodules.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/build-settlements-and-play-mobile-minigames.md`: NPC worker assignment and establishment workflows.
  - `docs/reference/platform-services.md`: Redis streams and test fixture conventions.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Frontdoor verification of settlement worker administration permissions.
  - **ADR-0002: Domain Events via eventsource-py**: Redis Streams CloudEvent verification across worker transitions.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean aggregate boundaries and test isolation.
  - **ADR-0008: Property-Based and Blackbox Testing**: Testing through public FastAPI routers and domain events without backdoor state mutation.
  - **ADR-0010: Continuous Integration Pipeline**: Fast, decoupled test execution in CI.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0024-settlement-haven-builder-and-establishment-ecosystem.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-establishment-ecosystem.md)
  - [`us-0073-assignable-npc-workers-and-social-relationships.md`](../../user_stories/accepted/us-0073-assignable-npc-workers-and-social-relationships.md)

## Detailed Specification & Implementation Plan
1. **Shared Fixtures (`tests/test_blackbox_npc_worker/conftest.py`)**:
   - Extract mock Redis event bus fixture, mock SpiceDB client, and TestClient app fixture (< 50 lines).
2. **Worker Assignment Tests (`tests/test_blackbox_npc_worker/test_worker_assignment.py`)**:
   - Test worker generation, establishment assignment, slot limits, and role compatibility (< 110 lines).
3. **Morale & Wage Tests (`tests/test_blackbox_npc_worker/test_morale_and_wages.py`)**:
   - Test weekly wage distribution, treasury deduction, unpaid grievance escalation, and morale swings (< 110 lines).
4. **Social Graph Tests (`tests/test_blackbox_npc_worker/test_social_graph.py`)**:
   - Test relationship synergy, rival workplace friction, rumor propagation, and friendship boons (< 110 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_npc_worker/` and verify all tests pass cleanly.

## INVEST Criteria Evaluation
- **Independent (I)**: Test reorganization without altering public test behavior or production code.
- **Negotiable (N)**: Split boundaries between assignment, morale, and social graph can be adjusted.
- **Valuable (V)**: Protects test suite maintainability and keeps test files < 130 lines.
- **Estimable (E)**: Pure refactoring with clear file divisions.
- **Small (S)**: Target test modules are each under 110 lines.
- **Testable (T)**: Self-testing; test suite must pass with full coverage.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_blackbox_npc_worker_engine.py` replaced by modular package `tests/test_blackbox_npc_worker/`.
2. All test sub-modules strictly < 130 lines each per Hard Invariant 6.
3. Tests pass via `uv run pytest tests/test_blackbox_npc_worker/`.
4. Code passes lint and typecheck (`uv run ruff check .` and `uv run ruff format --check .`).
