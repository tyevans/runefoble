---
id: '0276'
title: Settlement Bulletin Board Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-28
dependencies:
- TASK-0263
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0007
- ADR-0008
- ADR-0010
governing_prds:
- PRD-0024
governing_stories:
- US-0076
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/308
---
# TASK-0276: Settlement Bulletin Board Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_bulletin_board.py` (365 lines, 73.0% of limit) into modular test sub-suites under `tests/test_blackbox_bulletin_board/` (`conftest.py`, `test_bulletin_posting.py`, `test_wax_seals_and_ciphers.py`, `test_bounty_workflows.py`), ensuring all test sub-modules remain strictly < 130 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_bulletin_board.py` has grown to 365 lines in its initial implementation, testing bulletin posting, notice removal, wax seal verification, cipher puzzle decryption, bounty claims, and Redis stream event emission within a single module. As additional notice categories, anonymous rumors, and civic decrees are introduced, this suite will approach the 500-line invariant limit unless decoupled into focused submodules.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/build-settlements-and-play-mobile-minigames.md`: Notice board posting, bounty escrow, and cipher revelation.
  - `docs/reference/platform-services.md`: Event bus testing and FastAPI test client patterns.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Frontdoor verification of DM decree posting and player decryption permissions.
  - **ADR-0002: Domain Events via eventsource-py**: Redis Streams CloudEvent verification across bulletin transitions.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean aggregate boundaries and test isolation.
  - **ADR-0008: Property-Based and Blackbox Testing**: Testing through public FastAPI routers and domain events without backdoor state mutation.
  - **ADR-0010: Continuous Integration Pipeline**: Fast, decoupled test execution in CI.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0024-settlement-haven-builder-and-establishment-ecosystem.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-establishment-ecosystem.md)
  - [`us-0076-town-bulletin-board-and-civic-proclamations.md`](../../user_stories/accepted/us-0076-town-bulletin-board-and-civic-proclamations.md)

## Detailed Specification & Implementation Plan
1. **Shared Fixtures (`tests/test_blackbox_bulletin_board/conftest.py`)**:
   - Extract mock Redis event bus fixture, mock SpiceDB client, and TestClient app fixture (< 50 lines).
2. **Bulletin Posting & Query Tests (`tests/test_blackbox_bulletin_board/test_bulletin_posting.py`)**:
   - Test civic decrees, rumor posting, filter tabs, and active notice queries (< 110 lines).
3. **Wax Seals & Cipher Decryption Tests (`tests/test_blackbox_bulletin_board/test_wax_seals_and_ciphers.py`)**:
   - Test wax seal breaking, cipher puzzle decryption, player access control, and secret revelation (< 110 lines).
4. **Bounty Workflows & Removal Tests (`tests/test_blackbox_bulletin_board/test_bounty_workflows.py`)**:
   - Test bounty escrow claims, completion rewards, expiration, and notice removal (< 110 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_bulletin_board/` and verify all tests pass cleanly.

## INVEST Criteria Evaluation
- **Independent (I)**: Test refactoring without changing production code or test expectations.
- **Negotiable (N)**: Split boundaries between posting, ciphers, and bounties can be tuned.
- **Valuable (V)**: Protects test suite maintainability and keeps test files < 130 lines.
- **Estimable (E)**: Pure refactoring with clear file divisions.
- **Small (S)**: Target test modules are each under 110 lines.
- **Testable (T)**: Self-testing; test suite must pass with full coverage.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_blackbox_bulletin_board.py` replaced by modular package `tests/test_blackbox_bulletin_board/`.
2. All test sub-modules strictly < 130 lines each per Hard Invariant 6.
3. Tests pass via `uv run pytest tests/test_blackbox_bulletin_board/`.
4. Code passes lint and typecheck (`uv run ruff check .` and `uv run ruff format --check .`).
