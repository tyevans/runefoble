---
id: '0272'
title: Settlement Haven Aggregate Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-27
dependencies:
- TASK-0259
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0007
- ADR-0008
- ADR-0010
- ADR-0011
governing_prds:
- PRD-0024
governing_stories:
- US-0072
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/309
---
# TASK-0272: Settlement Haven Aggregate Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_settlement_haven_aggregate.py` (374 lines, 74.8% of limit) into modular test sub-suites under `tests/test_blackbox_settlement_haven/` (`conftest.py`, `test_founding_and_scale.py`, `test_establishment_construction.py`, `test_upgrades_and_events.py`), ensuring all test sub-modules remain strictly < 130 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_settlement_haven_aggregate.py` has grown to 374 lines in its initial implementation, testing settlement founding, establishment construction, tier upgrades, event publishing over Redis streams, and SpiceDB Zanzibar relationship verification within a single module. As additional district zoning rules and worker assignment assertions are introduced, this suite will approach the 500-line invariant limit unless decoupled into focused submodules.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/build-settlements-and-play-mobile-minigames.md`: Haven builder workflows, zoning, and tier upgrades.
  - `docs/reference/platform-services.md`: Redis streams and test fixture conventions.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Frontdoor verification of party and settlement ownership tuples.
  - **ADR-0002: Domain Events via eventsource-py**: Redis Streams CloudEvent verification across domain transitions.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean aggregate boundaries and test isolation.
  - **ADR-0008: Property-Based and Blackbox Testing**: Testing through public FastAPI routers and domain events without internal state mutation.
  - **ADR-0010: Continuous Integration Pipeline**: Fast, decoupled test execution in CI.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0024-settlement-haven-builder-and-establishment-ecosystem.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-establishment-ecosystem.md)
  - [`us-0072-settlement-haven-builder-and-establishment-zoning.md`](../../user_stories/accepted/us-0072-settlement-haven-builder-and-establishment-zoning.md)

## Detailed Specification & Implementation Plan
1. **Shared Fixtures (`tests/test_blackbox_settlement_haven/conftest.py`)**:
   - Extract mock Redis event bus fixture, MockSpiceDBClient fixture, and TestClient app fixture (< 50 lines).
2. **Founding & Scaling Tests (`tests/test_blackbox_settlement_haven/test_founding_and_scale.py`)**:
   - Test settlement founding, scale progression, and district capacity constraints (< 110 lines).
3. **Establishment Construction Tests (`tests/test_blackbox_settlement_haven/test_establishment_construction.py`)**:
   - Test establishment construction across Hospitality, Commerce, Civic, Faith, and Underworld categories (< 110 lines).
4. **Upgrades & Event Publishing Tests (`tests/test_blackbox_settlement_haven/test_upgrades_and_events.py`)**:
   - Test establishment tier upgrades, settlement tier upgrades, and Redis stream event emission assertions (< 110 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_settlement_haven/` and ensure all tests pass cleanly.

## INVEST Criteria Evaluation
- **Independent (I)**: Test refactoring without changing production code or test expectations.
- **Negotiable (N)**: Test function distribution across submodules can be tailored.
- **Valuable (V)**: Prevents test suite from breaching file size limits.
- **Estimable (E)**: Pure mechanical test suite decomposition.
- **Small (S)**: Target test modules are each under 110 lines.
- **Testable (T)**: Existing test coverage guarantees zero regression.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_blackbox_settlement_haven_aggregate.py` replaced by modular package `tests/test_blackbox_settlement_haven/`.
2. All test sub-modules strictly < 130 lines each per Hard Invariant 6.
3. Tests pass via `uv run pytest tests/test_blackbox_settlement_haven/`.
4. Code passes lint and typecheck (`uv run ruff check .` and `uv run ruff format --check .`).
