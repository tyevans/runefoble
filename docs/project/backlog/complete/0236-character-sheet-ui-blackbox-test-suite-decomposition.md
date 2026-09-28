---
id: '0236'
title: Character Sheet UI Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-27
dependencies:
- TASK-0107
- TASK-0189
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0007
- ADR-0008
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0006
governing_stories:
- US-0015
- US-0051
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/301
---
# TASK-0236: Character Sheet UI Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_character_sheet_ui.py` (395 lines, 79.0% of limit) into modular test sub-suites under `tests/test_blackbox_character_sheet_ui/` (`conftest.py`, `test_stats_rendering.py`, `test_inventory_grid.py`, `test_conditions_and_spells.py`), keeping all test modules strictly < 130 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_character_sheet_ui.py` contains 395 lines testing Lit Web Component rendering, ability score cards, drag-and-drop inventory slots, condition overlays, and spell preparation grids in a single test module. Approaching the file size threshold of 400 lines, decomposing it into focused sub-suites improves test maintenance and ensures strict compliance with Hard Invariant 6.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Frontdoor character sheet UI workflows.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Component mounting and DOM inspection.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular test package structure.
  - **ADR-0004: Lit Web Components and Storybook UI**: Component shadow DOM verification and UI events.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for character sheets.
  - **ADR-0008: Property-Based and Blackbox Testing**: Public frontdoor UI and DOM testing patterns.
  - **ADR-0010: Continuous Integration Pipeline**: Fast, reliable parallel test execution in CI.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Component isolation.

## Product & User Story References
- **Product Requirement**: [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)
- **User Stories**:
  - [`us-0015-interactive-digital-character-sheet.md`](../../user_stories/accepted/us-0015-interactive-digital-character-sheet.md)
  - [`us-0051-character-sheet-inventory-drag-drop-and-conditions.md`](../../user_stories/accepted/us-0051-character-sheet-inventory-drag-drop-and-conditions.md)

## Detailed Specification & Implementation Plan
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

## INVEST Criteria Evaluation
- **Independent (I)**: Test package restructuring without modifying application code or external APIs.
- **Negotiable (N)**: Submodule groupings can be fine-tuned.
- **Valuable (V)**: Prevents test suite from breaching 500-line invariant while improving readability.
- **Estimable (E)**: Pure mechanical test extraction.
- **Small (S)**: Resulting test submodules strictly < 130 lines each.
- **Testable (T)**: Existing test cases run and pass identically.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_blackbox_character_sheet_ui.py` replaced by modular sub-suites under `tests/test_blackbox_character_sheet_ui/`.
2. All test files strictly < 130 lines each.
3. Passes `uv run pytest tests/test_blackbox_character_sheet_ui/`.
4. Passes `uv run ruff check .` and `uv run ruff format --check .`.
