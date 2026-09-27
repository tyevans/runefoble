---
id: '0176'
title: West Marches UI Blackbox Test Suite Modular Decomposition
status: Proposed
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
Proposed

## Summary
Decompose `tests/test_blackbox_west_marches_ui.py` (379 lines, 75.8% of limit) into modular test submodules under `tests/test_blackbox_west_marches_ui/` (`test_manifest.py`, `test_atlas_pins.py`, `test_stronghold_dashboard.py`, `conftest.py`), keeping all test files < 150 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_west_marches_ui.py` tests UI manifests, interactive map pins, communal strongholds, and discovery logs in a single 379-line file. Approaching the file size limit, it must be decomposed into focused test modules for clarity and maintainability.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring.
- **ADR-0008: Property and Mutation Testing with Hypothesis**: Clean test fixtures.
- **ADR-0010: Continuous Integration Pipeline**: Parallelized test execution in CI.

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_west_marches_ui/conftest.py`)**:
   - Extract test client, authentication mocks, and atlas pin fixtures (< 80 lines).
2. **Manifest Tests (`tests/test_blackbox_west_marches_ui/test_manifest.py`)**:
   - Verify `/ui/manifest` and custom element registrations (< 100 lines).
3. **Atlas Pins Tests (`tests/test_blackbox_west_marches_ui/test_atlas_pins.py`)**:
   - Verify pin placement, filter toggles, and coordinate tracking (< 120 lines).
4. **Stronghold Dashboard Tests (`tests/test_blackbox_west_marches_ui/test_stronghold_dashboard.py`)**:
   - Verify facility upgrades, log updates, and shared resource metrics (< 120 lines).

## Definition of Done
- Test package created with all files strictly < 150 lines.
- `uv run pytest tests/test_blackbox_west_marches_ui/` passes.
- Code style passes `uv run ruff check .` and `uv run ruff format --check .`.
