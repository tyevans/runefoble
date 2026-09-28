---
id: '0225'
title: Campaign and Lobby Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-27
dependencies:
- TASK-0215
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0004
- ADR-0006
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0064
- US-0065
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/321
---
# TASK-0225: Campaign and Lobby Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_campaign_and_lobby.py` (338 lines, 67.6% of limit) into modular test submodules under `tests/test_blackbox_campaign_and_lobby/` (`conftest.py`, `test_campaign_lifecycle.py`, `test_party_assignment.py`, `test_session_lobby.py`), keeping all test files strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_campaign_and_lobby.py` covers campaign creation, Zanzibar authorization, roster party assignments, and lobby readiness transitions in a single monolithic test file of 338 lines. As multi-party West Marches integration tests and real-time WebSocket session launch assertions are expanded, this test file will breach the 500-line invariant unless decomposed.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/manage-campaign-lifecycle-and-invites.md`: Campaign creation, Zanzibar roles, and shareable invites.
  - `docs/how-to/coordinate-game-session-lobby-and-readiness.md`: Pre-game lobby readiness, player presence, and absentee AI stand-ins.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Cross-context authorization testing.
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring under UV workspace.
  - **ADR-0004: Lit Web Components and Storybook UI**: Microfrontend integration testing.
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event emission and subscription testing.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
  - **ADR-0013: Modular Microfrontend Decomposition**: Component integration verification.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
  - [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
  - [`us-0064-character-roster-management-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-management-and-party-assignment.md)
  - [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)

## Detailed Specification & Implementation Plan
1. **Shared Fixtures (`tests/test_blackbox_campaign_and_lobby/conftest.py`)**:
   - Extract test client initialization, mock Redis bus, SpiceDB client configuration, and store reset fixtures (< 60 lines).
2. **Campaign Lifecycle Tests (`tests/test_blackbox_campaign_and_lobby/test_campaign_lifecycle.py`)**:
   - Extract campaign creation, Zanzibar ownership checks, and invite management tests (< 110 lines).
3. **Party Assignment Tests (`tests/test_blackbox_campaign_and_lobby/test_party_assignment.py`)**:
   - Extract character roster creation, party assignment, and capacity limit tests (< 100 lines).
4. **Session Lobby Tests (`tests/test_blackbox_campaign_and_lobby/test_session_lobby.py`)**:
   - Extract player readiness toggles, absentee stand-in selection, and session transition triggers (< 110 lines).
5. **Verification**:
   - Remove root test module `test_blackbox_campaign_and_lobby.py` and run `uv run pytest tests/test_blackbox_campaign_and_lobby/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Test reorganization without modifying production routes or event definitions.
- **Negotiable (N)**: Test file partitioning boundaries can be tuned.
- **Valuable (V)**: Protects the campaign and lobby integration suite from breaching the 500-line invariant limit.
- **Estimable (E)**: Direct test extraction into dedicated test modules.
- **Small (S)**: Target files will each be strictly < 120 lines.
- **Testable (T)**: Pytest execution verifies 100% test pass parity.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_blackbox_campaign_and_lobby/` package created with submodules strictly < 130 lines.
2. Root `test_blackbox_campaign_and_lobby.py` cleanly removed.
3. All tests pass via `uv run pytest tests/test_blackbox_campaign_and_lobby/`.
4. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
