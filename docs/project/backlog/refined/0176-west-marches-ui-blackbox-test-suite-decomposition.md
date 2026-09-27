---
id: '0176'
title: West Marches UI Blackbox Test Suite Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0127
- TASK-0135
governing_adrs:
- ADR-0003
- ADR-0008
- ADR-0010
governing_prds:
- PRD-0018
governing_stories:
- US-0050
- US-0058
target_release: 0.7.0
---

# TASK-0176: West Marches UI Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_west_marches_ui.py` (379 lines, 75.8% of limit) into modular test submodules under `tests/test_blackbox_west_marches_ui/` (`test_manifest.py`, `test_atlas_pins.py`, `test_stronghold_dashboard.py`, `conftest.py`), keeping all test files < 150 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_west_marches_ui.py` tests UI manifests, interactive map pins, communal strongholds, and discovery logs in a single 379-line file. Approaching the file size limit, it must be decomposed into focused test modules for clarity and maintainability.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring.
- **ADR-0008: Property and Mutation Testing with Hypothesis**: Clean test fixtures and invariant testing.
- **ADR-0010: Continuous Integration Pipeline**: Parallelized test execution in CI.

## Product & User Story References
- **Product Requirement**: [`prd-0018-cross-campaign-trade-and-caravans.md`](../../product/accepted/prd-0018-cross-campaign-trade-and-caravans.md)
- **User Story**: [`us-0050-collaborative-campaign-world-atlas-and-codex.md`](../../user_stories/accepted/us-0050-collaborative-campaign-world-atlas-and-codex.md)
- **User Story**: [`us-0058-cross-campaign-caravan-trading-and-contracts.md`](../../user_stories/accepted/us-0058-cross-campaign-caravan-trading-and-contracts.md)

## Detailed Specification & Implementation Plan
1. **Shared Fixtures (`tests/test_blackbox_west_marches_ui/conftest.py`)**:
   - Extract test client, authentication mocks, and atlas pin fixtures (< 80 lines).
2. **Manifest Tests (`tests/test_blackbox_west_marches_ui/test_manifest.py`)**:
   - Verify `/ui/manifest` and custom element registrations (< 100 lines).
3. **Atlas Pins Tests (`tests/test_blackbox_west_marches_ui/test_atlas_pins.py`)**:
   - Verify pin placement, filter toggles, and coordinate tracking (< 120 lines).
4. **Stronghold Dashboard Tests (`tests/test_blackbox_west_marches_ui/test_stronghold_dashboard.py`)**:
   - Verify facility upgrades, log updates, and shared resource metrics (< 120 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Test package restructuring without changing assertion semantics or production APIs.
- **Negotiable (N)**: Test organization can be categorized by endpoint and user journey.
- **Valuable (V)**: Prevents test file growth beyond 400 lines and isolates fixture setup.
- **Estimable (E)**: Pure mechanical test extraction with existing passing assertions.
- **Small (S)**: Bounded strictly to `tests/test_blackbox_west_marches_ui/`; all modules < 150 lines.
- **Testable (T)**: Frontdoor verification via `pytest tests/test_blackbox_west_marches_ui/`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Test Suite Architecture**:
   - Test package created with all files strictly < 150 lines per Hard Invariant 6.
   - Original monolithic `tests/test_blackbox_west_marches_ui.py` removed.
2. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest tests/test_blackbox_west_marches_ui/`.
3. **Quality Gates**:
   - Code style passes `uv run ruff check .` and `uv run ruff format --check .`.
