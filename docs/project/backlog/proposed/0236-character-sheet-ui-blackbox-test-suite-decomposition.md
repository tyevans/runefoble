---
id: '0236'
title: Character Sheet UI Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0107
- TASK-0189
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0006
governing_stories:
- US-0015
- US-0051
target_release: 0.8.0
---

# TASK-0236: Character Sheet UI Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_character_sheet_ui.py` (318 lines, 63.6% of limit) into modular test sub-suites under `tests/test_blackbox_character_sheet_ui/` (`test_stats_rendering.py`, `test_inventory_grid.py`, `test_conditions_and_spells.py`), keeping all test modules strictly < 130 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_character_sheet_ui.py` contains 318 lines testing Lit Web Component rendering, ability score cards, drag-and-drop inventory slots, condition overlays, and spell preparation grids in a single test module. Approaching the file size threshold, decomposing it into focused sub-suites improves test maintenance and ensures compliance with Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular test package structure.
- **ADR-0004: Lit Web Components and Storybook UI**: Component shadow DOM verification and UI events.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for character sheets.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Microfrontend manifest and component isolation.

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_character_sheet_ui/conftest.py`)**:
   - Extract mock character models, Lit component mounting helpers, and session fixtures (< 60 lines).
2. **Stats & Vitals Tests (`tests/test_blackbox_character_sheet_ui/test_stats_rendering.py`)**:
   - Test ability scores, HP meters, temporary HP, and proficiency badges (< 100 lines).
3. **Inventory & Encumbrance Tests (`tests/test_blackbox_character_sheet_ui/test_inventory_grid.py`)**:
   - Test equipment slots, item addition/removal, weight calculations, and encumbrance bars (< 100 lines).
4. **Conditions & Spells Tests (`tests/test_blackbox_character_sheet_ui/test_conditions_and_spells.py`)**:
   - Test condition tags, exhaustion indicators, spell slot pips, and prepared spell lists (< 100 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_character_sheet_ui/` and ensure all tests pass cleanly.

## Definition of Done
- `tests/test_blackbox_character_sheet_ui.py` replaced by modular sub-suites under `tests/test_blackbox_character_sheet_ui/`.
- All test files strictly < 130 lines each.
- Passes `uv run pytest tests/test_blackbox_character_sheet_ui/`.
- Passes `uv run ruff check .` and `uv run ruff format --check .`.
