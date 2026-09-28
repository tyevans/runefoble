---
id: '0281'
title: Merchant Haggling Blackbox Test Suite Modular Decomposition
status: Refined
created: 2026-09-28
dependencies:
- TASK-0262
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0075
target_release: 0.8.0
---

# TASK-0281: Merchant Haggling Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_merchant_haggling.py` (359 lines, 71.8% of limit) into modular test submodules under `tests/test_blackbox_merchant_haggling/` (`conftest.py`, `test_bargain_flow.py`, `test_rhetoric_moves.py`, `test_dm_arbitration.py`), ensuring all test files remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_merchant_haggling.py` tests haggling session initialization, player rhetoric moves, merchant mood calculations, patience degradation, DM live price overrides, and deal acceptance in a single 359-line test module. As multi-currency exchange and complex trade bundle tests are added, this test file will breach the 500-line limit unless decomposed into focused, single-responsibility submodules.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/run-tavern-minigames-and-merchant-haggling.md`: Bartering mechanics, rhetoric moves, and DM arbitration.
  - `docs/reference/tavern-and-merchants-events.md`: CloudEvents schemas and event flows for merchant haggling.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring.
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Real-time event bus verification.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation across test suites.
  - **ADR-0010: Continuous Integration Pipeline**: Rapid regression feedback.
  - **ADR-0013: Modular Decomposition**: All test modules kept strictly < 130 lines.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
  - [`us-0075-dynamic-merchant-haggling-with-dm-arbitration.md`](../../user_stories/accepted/us-0075-dynamic-merchant-haggling-with-dm-arbitration.md)

## Detailed Specification & Implementation Plan
1. **Shared Fixtures Submodule (`tests/test_blackbox_merchant_haggling/conftest.py`)**:
   - Extract test client setup, mock merchant entities, item catalogs, and token auth fixtures (< 70 lines).
2. **Bargain Flow Tests Submodule (`tests/test_blackbox_merchant_haggling/test_bargain_flow.py`)**:
   - Extract session start, price range checks, counter-offer rounds, and walk-away tests (< 110 lines).
3. **Rhetoric & Temperament Tests Submodule (`tests/test_blackbox_merchant_haggling/test_rhetoric_moves.py`)**:
   - Extract flattery, intimidation, bundling, and patience threshold failure tests (< 110 lines).
4. **DM Arbitration Tests Submodule (`tests/test_blackbox_merchant_haggling/test_dm_arbitration.py`)**:
   - Extract DM price overrides, dialogue injections, deal vetoes, and approval events (< 110 lines).
5. **Verification**:
   - Remove root test file and run `uv run pytest tests/test_blackbox_merchant_haggling/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Test modularization that does not affect application runtime behavior.
- **Negotiable (N)**: Test grouping can be tuned across submodules.
- **Valuable (V)**: Protects the second largest test suite (359 lines) from breaching the 500-line invariant limit.
- **Estimable (E)**: Straightforward refactoring of test functions into cohesive test files.
- **Small (S)**: Each extracted test file strictly < 130 lines.
- **Testable (T)**: Self-testing; test suite must execute cleanly with 100% pass rate.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_blackbox_merchant_haggling/` created and root file removed.
2. All extracted test submodules strictly < 130 lines each per Hard Invariant 6.
3. 100% test coverage and parity preserved across all test cases.
4. Passes all tests via `uv run pytest tests/test_blackbox_merchant_haggling/`.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
