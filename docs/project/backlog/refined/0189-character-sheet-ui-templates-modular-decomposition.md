---
id: '0189'
title: Character Sheet UI Templates Modular Decomposition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0107
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0006
governing_stories:
- US-0015
- US-0051
target_release: 0.7.0
---

# TASK-0189: Character Sheet UI Templates Modular Decomposition

## Status
Refined

## Summary
Decompose `services/character_sheet/ui/src/runefoble-character-sheet.templates.ts` (343 lines, 68.6% of limit) into modular template modules under `services/character_sheet/ui/src/templates/` (`stats.template.ts`, `inventory.template.ts`, `conditions.template.ts`, `spells.template.ts`), keeping each template file strictly < 120 lines per Hard Invariant 6 and ADR-0013.

## Problem Statement
`services/character_sheet/ui/src/runefoble-character-sheet.templates.ts` contains 343 lines of Lit HTML render templates for ability scores, health indicators, equipment slots, encumbrance meters, condition badges, and spell slots. As Milestone 9 introduces mobile responsive layout variants and absentee directive overrides, this file will soon exceed 400 lines unless modularized into dedicated sub-templates.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Clean separation of Lit templates and component logic.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Adherence to Bauhaus UI tokens and semantic styling.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: UI isolation within `services/character_sheet/ui/`.

## Detailed Specification & Implementation Plan
1. **Stats Template (`services/character_sheet/ui/src/templates/stats.template.ts`)**:
   - Ability scores, hit points, proficiency bonuses, and saving throws (< 100 lines).
2. **Inventory Template (`services/character_sheet/ui/src/templates/inventory.template.ts`)**:
   - Grid slots, equipment items, weight calculation, and encumbrance bars (< 100 lines).
3. **Conditions Template (`services/character_sheet/ui/src/templates/conditions.template.ts`)**:
   - Status badges, active debuffs, and tooltips (< 80 lines).
4. **Spells Template (`services/character_sheet/ui/src/templates/spells.template.ts`)**:
   - Spell slot counters and prepared spell badges (< 80 lines).
5. **Aggregator Facade (`services/character_sheet/ui/src/runefoble-character-sheet.templates.ts`)**:
   - Re-export modular template renderers to preserve the existing component API (< 50 lines).
6. **Verification**:
   - Verify Storybook builds and character sheet stories render without error.
   - Run tests via `uv run pytest tests/test_blackbox_character_sheet_ui.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Template refactoring isolated to `services/character_sheet/ui/src/templates/`.
- **Negotiable (N)**: Sub-template boundaries cleanly match character sheet functional tabs and panels.
- **Valuable (V)**: Safeguards against Hard Invariant 6 (500 lines) and improves template readability.
- **Estimable (E)**: Pure Lit template HTML refactoring preserving existing prop contracts.
- **Small (S)**: Bounded strictly to `services/character_sheet/ui/`; all sub-templates < 120 lines.
- **Testable (T)**: Frontdoor verification through Storybook and blackbox UI tests.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `runefoble-character-sheet.templates.ts` reduced to strictly < 60 lines.
   - Extracted submodules under `templates/` strictly < 120 lines each.
2. **Frontdoor Test Verification**:
   - `uv run pytest tests/test_blackbox_character_sheet_ui.py` passes cleanly.
3. **Quality Gates**:
   - Storybook stories render without errors.
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
