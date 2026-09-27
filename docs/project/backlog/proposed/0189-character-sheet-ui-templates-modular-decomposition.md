---
id: '0189'
title: Character Sheet UI Templates Modular Decomposition
status: Proposed
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
Proposed

## Summary
Decompose `services/character_sheet/ui/src/runefoble-character-sheet.templates.ts` (343 lines, 68.6% of limit) into modular template modules under `services/character_sheet/ui/src/templates/` (`stats.template.ts`, `inventory.template.ts`, `conditions.template.ts`, `spells.template.ts`), keeping each template file strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`services/character_sheet/ui/src/runefoble-character-sheet.templates.ts` contains 343 lines of Lit HTML render templates for ability scores, health indicators, equipment slots, encumbrance meters, condition badges, and spell slots. As Milestone 9 introduces mobile responsive layout variants and absentee directive overrides, this file will soon exceed 400 lines unless modularized into dedicated sub-templates.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Visualizer & Lit Component Architecture**: Clean separation of Lit templates and component logic.
- **ADR-0012: Theming Tokens & Bauhaus Design System**: Adherence to Bauhaus UI tokens and semantic styling.
- **ADR-0013: Microfrontend Bounded Context Architecture**: UI isolation within `services/character_sheet/ui/`.

## Scope of Work
1. **Modular Template Subdirectory (`services/character_sheet/ui/src/templates/`)**:
   - `stats.template.ts`: Ability scores, hit points, proficiency bonuses, and saving throws (< 100 lines).
   - `inventory.template.ts`: Grid slots, equipment items, weight calculation, and encumbrance bars (< 100 lines).
   - `conditions.template.ts`: Status badges, active debuffs, and tooltips (< 80 lines).
   - `spells.template.ts`: Spell slot counters and prepared spell badges (< 80 lines).
2. **Aggregator Facade (`services/character_sheet/ui/src/runefoble-character-sheet.templates.ts`)**:
   - Re-export modular template renderers to preserve the existing component API (< 50 lines).
3. **Verification**:
   - Verify Storybook builds and character sheet stories render without error.
   - Verify `tests/test_blackbox_character_sheet_ui.py` passes cleanly.

## Definition of Done
- `runefoble-character-sheet.templates.ts` reduced to < 60 lines.
- Submodules in `templates/` strictly < 120 lines each.
- Storybook stories and microfrontend tests pass cleanly.
