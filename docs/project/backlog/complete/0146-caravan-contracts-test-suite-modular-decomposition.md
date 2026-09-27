---
id: '0146'
title: Caravan Contracts Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0129
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0011
- ADR-0013
governing_prds:
- PRD-0007
governing_stories:
- US-0058
target_release: 0.5.0
pr_url: https://github.com/tyevans/runefoble/pull/161
---
# TASK-0146: Caravan Contracts Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_caravan_contracts.py` (476 lines, 95.2% of limit) into modular frontdoor blackbox test files under `tests/test_blackbox_caravan_contracts/` (`conftest.py`, `test_board_posting.py`, `test_cross_campaign_auth.py`, `test_caravan_lifecycle.py`, `test_caravan_destruction_and_ui.py`), guaranteeing all test files remain < 150 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_caravan_contracts.py` has grown to 476 lines—dangerously close to the 500-line hard invariant ceiling. It covers notice board queries, cross-campaign acceptance, Zanzibar party leader permissions, caravan escort hazards/ambushes, and economy reward distribution in a single monolithic test file.

## Governing Architecture & ADRs
- **ADR-0001: Fine-Grained Authorization with SpiceDB Zanzibar**: Authorization enforcement for contract acceptance and officer role validation.
- **ADR-0006: Redis Streams Event Bus Architecture**: Verification of `frontier.caravan.dispatched`, `frontier.contract.fulfilled`, and related domain events.
- **ADR-0011: eventsource-py Core Event Sourcing**: Aggregate lifecycle validation through public HTTP frontdoors.
- **ADR-0013: Microfrontend Architecture & Component Manifest**: UI manifest endpoint validation for caravan notice boards.

## Product & User Story References
- **Product Requirement**: [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
- **User Story**: [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)

## Detailed Specification & Implementation Plan
1. **Fixtures & Shared Harness (`tests/test_blackbox_caravan_contracts/conftest.py`)**:
   - Extract `mock_bus`, `client`, and test helper setup (< 50 lines).
2. **Board Posting & Queries (`tests/test_blackbox_caravan_contracts/test_board_posting.py`)**:
   - Extract tests for posting mercenary contracts, risk-level metadata, reward deposits, and notice board filtering (< 130 lines).
3. **Cross-Campaign Acceptance & Auth (`tests/test_blackbox_caravan_contracts/test_cross_campaign_auth.py`)**:
   - Extract tests for acceptance by external campaigns, Zanzibar high-tier officer authorization, and 403 denial verification (< 120 lines).
4. **Escort Lifecycle & Settlement Fulfillment (`tests/test_blackbox_caravan_contracts/test_caravan_lifecycle.py`)**:
   - Extract tests for caravan dispatch, waypoint advancement, combat ambushes, damage tracking, and destination settlement economy payout (< 140 lines).
5. **Caravan Destruction & UI Manifest (`tests/test_blackbox_caravan_contracts/test_caravan_destruction_and_ui.py`)**:
   - Extract tests for fatal ambushes, contract loss states, forfeit of deposits, and `/ui/manifest` frontdoor registration (< 110 lines).
6. **Deprecation Migration**:
   - Replace monolithic `tests/test_blackbox_caravan_contracts.py` with the modular directory suite.

## INVEST Criteria Evaluation
- **Independent (I)**: Test reorganization with zero production code changes.
- **Negotiable (N)**: Test boundaries can be tuned.
- **Valuable (V)**: Eliminates imminent Hard Invariant 6 violation and speeds up targeted test execution.
- **Estimable (E)**: Standard pytest suite modularization.
- **Small (S)**: Bounded strictly to `tests/test_blackbox_caravan_contracts/`; all files < 150 lines.
- **Testable (T)**: Validated by 100% pass rate across the decomposed suite.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Architecture**:
   - `tests/test_blackbox_caravan_contracts/` directory created with 5 focused files.
   - Zero files exceeding 160 lines.
2. **Test Suite Verification**:
   - `uv run pytest tests/test_blackbox_caravan_contracts/` passes cleanly.
3. **Quality Gates**:
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
