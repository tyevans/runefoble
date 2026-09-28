---
id: '0204'
title: Character Sheet Component Action Handlers and State Modular Decomposition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0009
- TASK-0107
- TASK-0189
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0006
governing_stories:
- US-0015
- US-0051
target_release: 0.7.0
---

# TASK-0204: Character Sheet Component Action Handlers and State Modular Decomposition

## Status
Refined

## Summary
Decompose `services/character_sheet/ui/src/runefoble-character-sheet.ts` (319 lines, 63.8% of limit) by extracting equipment slot mutation handlers, condition toggle callbacks, and spell slot consumption utilities into `runefoble-character-sheet.actions.ts`, keeping the main component file strictly < 150 lines per Hard Invariant 6 and ADR-0013.

## Problem Statement
`services/character_sheet/ui/src/runefoble-character-sheet.ts` contains extensive action handler methods (`handleEquipSlot`, `handleConditionToggle`, `handleSpellSlotChange`, `handleHpDelta`) and optimistic client mutation dispatchers directly embedded inside the LitElement controller. While rendering templates were previously separated into `runefoble-character-sheet.templates.ts`, the interactive mutations and state calculations remain tightly coupled in the controller file, which will breach the 400-line warning threshold as additional character inventory and attunement rules are added.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Design System**: Clean separation of state, controllers, and presentation layers.
- **ADR-0007: Domain-Driven Design Architecture**: Clean boundaries for character equipment and inventory state mutators.
- **ADR-0013: Microfrontend Bounded Context Architecture**: UI encapsulation within `services/character_sheet/ui/`.

## Detailed Specification & Implementation Plan
1. **Actions Submodule (`services/character_sheet/ui/src/runefoble-character-sheet.actions.ts`)**:
   - Extract pure state mutation helpers and custom event dispatching functions for inventory item slots, HP calculations, condition toggles, and spell slot usage (< 120 lines).
2. **Component Controller Refactoring (`services/character_sheet/ui/src/runefoble-character-sheet.ts`)**:
   - Delegate event handler logic to imported action helpers, leaving the controller focused on lifecycle hooks and property synchronization (< 150 lines).
3. **Verification**:
   - Verify character sheet Storybook stories and interactive events continue functioning without error.
   - Run blackbox tests in `tests/test_blackbox_character_sheet_ui.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Isolated to the character sheet UI controller and its new actions module.
- **Negotiable (N)**: Action helper interfaces can be pure functions taking current state and returning updated state.
- **Valuable (V)**: Drastically improves testability of character sheet mutations in isolation and ensures compliance with Hard Invariant 6.
- **Estimable (E)**: Pure extraction of event handler methods into utility functions.
- **Small (S)**: Scope strictly isolated to character sheet client state operations (< 150 lines per file).
- **Testable (T)**: Frontdoor verification via Storybook interaction and microfrontend blackbox tests.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `runefoble-character-sheet.ts` reduced to < 150 lines.
   - `runefoble-character-sheet.actions.ts` created and strictly < 130 lines.
2. **Frontdoor Verification**:
   - Equipment changes, HP adjustments, condition toggles, and spell slot expending function identically.
   - Storybook stories render without errors.
   - Microfrontend blackbox tests pass cleanly via `uv run pytest tests/test_blackbox_character_sheet_ui.py`.
3. **Quality Gates**:
   - Frontend and Python test suites pass cleanly.
