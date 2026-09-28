---
id: '0268'
title: Radial Menu and AoE Templates Test Suite Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0125
governing_adrs:
- ADR-0004
- ADR-0006
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0013
governing_stories:
- US-0056
target_release: 0.8.0
---

# TASK-0268: Radial Menu and AoE Templates Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_radial_menu_and_aoe.py` (303 lines) into modular submodules under `tests/test_blackbox_radial_menu_and_aoe/` (`conftest.py`, `test_radial_actions.py`, `test_aoe_templates.py`, `test_geometry_rotation.py`), keeping all test files strictly < 120 lines.

## Problem Statement
`tests/test_blackbox_radial_menu_and_aoe.py` covers radial action execution, AoE template geometry, and rotational snapping calculations within a single test suite. As 3D dice physics collision and dynamic line-of-sight triggers add further spatial tests, this module will exceed the 500-line invariant limit unless modularized into focused test units.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Radial token action menu and template component integration.
- **ADR-0006: Redis Streams Event Bus**: Event verification for `TokenActionExecuted` and `AoETemplatePlaced`.
- **ADR-0007: Domain-Driven Design Architecture**: Board state domain segregation.
- **ADR-0013: Modular Microfrontend Decomposition**: Clean test separation by concern.

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_radial_menu_and_aoe/conftest.py`)**:
   - Extract board setup, token creation fixtures, and test client helpers (< 50 lines).
2. **Radial Action Tests (`tests/test_blackbox_radial_menu_and_aoe/test_radial_actions.py`)**:
   - Extract Dodge, Dash, Disengage, and Attack action executions and validations (< 95 lines).
3. **AoE Placement Tests (`tests/test_blackbox_radial_menu_and_aoe/test_aoe_templates.py`)**:
   - Extract circle, cone, line, and square template placements and boundary checks (< 90 lines).
4. **Rotation and Geometry Tests (`tests/test_blackbox_radial_menu_and_aoe/test_geometry_rotation.py`)**:
   - Extract 15-degree angle snapping, targeted token collision detection, and multi-token queries (< 95 lines).
5. **Verification**:
   - Remove root test module `test_blackbox_radial_menu_and_aoe.py` and run `uv run pytest tests/test_blackbox_radial_menu_and_aoe/`.

## Definition of Done
- `tests/test_blackbox_radial_menu_and_aoe/` package created with submodules strictly < 120 lines.
- All test cases pass via `uv run pytest tests/test_blackbox_radial_menu_and_aoe/`.
- Zero lint or formatting errors (`uv run ruff check .` and `uv run ruff format --check .`).
