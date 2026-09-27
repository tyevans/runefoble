---
id: '0145'
title: West Marches Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0127
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0011
governing_prds:
- PRD-0007
governing_stories:
- US-0058
target_release: 0.5.0
pr_url: https://github.com/tyevans/runefoble/pull/162
---
# TASK-0145: West Marches Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_west_marches.py` (402 lines, approaching limit) into specialized, domain-focused test submodules under `tests/test_blackbox_west_marches/` (`conftest.py`, `test_world_registration.py`, `test_discovery_synchronization.py`, `test_caravan_transit.py`, `test_security_isolation.py`), ensuring all test files remain < 150 lines per Hard Invariant 6.

## Problem Statement
Following the merge of TASK-0127, `tests/test_blackbox_west_marches.py` spans 402 lines covering multi-party discovery synchronization, scheduled caravan transit, and SpiceDB Zanzibar multi-tenancy access control. Proactively decomposing it safeguards against breaching Hard Invariant 6 (< 500 lines) and enables parallel test execution.

## Governing Architecture & ADRs
- **ADR-0001: Fine-Grained Authorization with SpiceDB Zanzibar**: Multi-campaign party isolation tests.
- **ADR-0006: Redis Streams Event Bus Architecture**: Distributed world state synchronization event tests.
- **ADR-0011: eventsource-py Core Event Sourcing**: Aggregate reload and projection verification tests.

## Product & User Story References
- **Product Requirement**: [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
- **User Story**: [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)

## Detailed Specification & Implementation Plan
1. **Fixtures & Shared Harness (`tests/test_blackbox_west_marches/conftest.py`)**:
   - Extract `mock_bus`, `client`, and shared party session fixtures (< 50 lines).
2. **World Registration & Joining (`tests/test_blackbox_west_marches/test_world_registration.py`)**:
   - Extract tests for establishing persistent frontier worlds, linking campaigns, and duplicate registration validation (< 110 lines).
3. **Discovery Synchronization (`tests/test_blackbox_west_marches/test_discovery_synchronization.py`)**:
   - Extract tests for waypoint sharing, expedition log broadcast, and shared fog-of-war landmark discovery (< 130 lines).
4. **Caravan Transit & Trade (`tests/test_blackbox_west_marches/test_caravan_transit.py`)**:
   - Extract tests for caravan departure scheduling, transit hazard events, and trade ledger updates (< 130 lines).
5. **Security & Zanzibar Multi-Tenancy (`tests/test_blackbox_west_marches/test_security_isolation.py`)**:
   - Extract tests for cross-party boundary isolation, secret DM notes redaction, and unauthorized modification rejections (< 120 lines).
6. **Deprecation Migration**:
   - Safely remove monolithic `tests/test_blackbox_west_marches.py` with pytest discovering the new directory suite.

## INVEST Criteria Evaluation
- **Independent (I)**: Test reorganization with zero production code changes or external runtime dependencies.
- **Negotiable (N)**: Split boundaries between test modules can be adjusted.
- **Valuable (V)**: Prevents technical debt accumulation and guarantees hard invariant compliance.
- **Estimable (E)**: Straightforward pytest suite decomposition.
- **Small (S)**: Bounded to `tests/test_blackbox_west_marches/`; all files < 150 lines.
- **Testable (T)**: Validated by ensuring 100% of existing tests pass cleanly.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Architecture**:
   - `tests/test_blackbox_west_marches/` package created with focused submodules.
   - Zero files exceeding 160 lines.
2. **Test Suite Verification**:
   - `uv run pytest tests/test_blackbox_west_marches/` passes with 100% success rate.
3. **Quality Gates**:
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
