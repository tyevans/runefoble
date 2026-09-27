---
id: '0204'
title: Character Sheet Component Action Handlers and State Modular Decomposition
status: Proposed
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
Proposed

## Summary
Decompose `services/character_sheet/ui/src/runefoble-character-sheet.ts` (320 lines, 64.0% of limit) by extracting equipment slot mutation handlers, condition toggle callbacks, and spell slot consumption utilities into `runefoble-character-sheet.actions.ts`, keeping the main component file strictly < 150 lines per Hard Invariant 6 and ADR-0013.

## Problem Statement
`services/character_sheet/ui/src/runefoble-character-sheet.ts` contains extensive action handler methods (`handleEquipSlot`, `handleConditionToggle`, `handleSpellSlotChange`, `handleHpDelta`) and optimistic client mutation dispatchers directly embedded inside the LitElement controller. While rendering templates were separated into `runefoble-character-sheet.templates.ts`, the interactive mutations and state calculations remain tightly coupled in the controller file.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Design System**: Clean separation of state, controllers, and presentation layers.
- **ADR-0007: Domain-Driven Design Architecture**: Clean boundaries for character equipment and inventory state mutators.
- **ADR-0013: Microfrontend Bounded Context Architecture**: UI encapsulation within `services/character_sheet/ui/`.

## Scope of Work
1. **Actions Module (`services/character_sheet/ui/src/runefoble-character-sheet.actions.ts`)**:
   - Extract pure state mutation helpers and custom event dispatching functions for inventory item slots, HP calculations, condition toggles, and spell slot usage (< 120 lines).
2. **Component Controller Refactoring (`services/character_sheet/ui/src/runefoble-character-sheet.ts`)**:
   - Delegate event handler logic to imported action helpers (< 150 lines).
3. **Verification**:
   - Verify character sheet Storybook stories and interactive events continue functioning properly.
   - Run blackbox tests in `tests/test_blackbox_character_sheet_ui.py`.

## Definition of Done
- `runefoble-character-sheet.ts` reduced to < 150 lines.
- `runefoble-character-sheet.actions.ts` created and strictly < 130 lines.
- Storybook stories render without errors.
- Microfrontend blackbox tests pass cleanly.
