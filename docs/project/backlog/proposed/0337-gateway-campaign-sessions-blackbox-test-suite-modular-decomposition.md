---
id: '0337'
title: Gateway Campaign Sessions Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0246
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0021
governing_stories:
- US-0062
- US-0064
target_release: 0.8.0
---

# TASK-0337: Gateway Campaign Sessions Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_gateway_campaign_sessions.py` (286 lines, 57.2% of limit) into modular test submodules under `tests/test_blackbox_gateway_campaign_sessions/` (`test_permissions.py`, `test_creation_and_lifecycle.py`, `test_isolation.py`), ensuring all test modules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_gateway_campaign_sessions.py` validates gateway campaign session creation, Zanzibar authorization permissions across member/DM roles, session lifecycle transitions (lobby, active, completed), and cross-campaign data isolation in a single 286-line file. As session scheduling and multi-table synchronization tests expand, modularization is required before it nears the 500-line limit.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/coordinate-game-session-lobby-and-readiness.md`: Pre-game assembly, session creation, and readiness verification.
  - `docs/how-to/manage-campaign-lifecycle-and-invites.md`: Campaign membership and SpiceDB Zanzibar role enforcement.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Fine-Grained Authorization**: Session creation and listing permissions.
  - **ADR-0005: Zitadel Authentication and Identity**: User identity propagation.
  - **ADR-0007: Domain-Driven Design Architecture**: Gateway API session store.
  - **ADR-0013: Modular Decomposition**: Single-responsibility test modules strictly < 150 lines.

## Scope of Work & Implementation Plan
1. **Zanzibar Permission Tests (`tests/test_blackbox_gateway_campaign_sessions/test_permissions.py`)**:
   - Extract non-member 403 rejections, member view permissions, and owner/DM `run_session` assertions (< 90 lines).
2. **Session Creation and Lifecycle Tests (`tests/test_blackbox_gateway_campaign_sessions/test_creation_and_lifecycle.py`)**:
   - Extract session creation (HTTP 201), status transitions, active vs lobby listing, and metadata retrieval (< 100 lines).
3. **Cross-Campaign Isolation Tests (`tests/test_blackbox_gateway_campaign_sessions/test_isolation.py`)**:
   - Extract multi-campaign session boundaries and unauthorized cross-campaign access assertions (< 90 lines).
4. **Verification**:
   - Safely remove monolithic `tests/test_blackbox_gateway_campaign_sessions.py` and verify all tests pass via `uv run pytest tests/test_blackbox_gateway_campaign_sessions/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Test refactoring is self-contained in the test suite and alters no production gateway behavior.
- **Negotiable (N)**: Sub-suite file names can be tuned cleanly.
- **Valuable (V)**: Protects test maintainability and adheres to Hard Invariant 6.
- **Estimable (E)**: Discrete test cases with existing 100% passing coverage.
- **Small (S)**: Each extracted test file will be strictly < 110 lines.
- **Testable (T)**: Directly executable via `uv run pytest tests/test_blackbox_gateway_campaign_sessions/`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_blackbox_gateway_campaign_sessions.py` decomposed into modular submodules under `tests/test_blackbox_gateway_campaign_sessions/`.
2. All extracted submodules strictly < 110 lines per Hard Invariant 6.
3. 100% of blackbox assertions pass via `uv run pytest tests/test_blackbox_gateway_campaign_sessions/`.
4. Monolithic `tests/test_blackbox_gateway_campaign_sessions.py` safely removed.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
