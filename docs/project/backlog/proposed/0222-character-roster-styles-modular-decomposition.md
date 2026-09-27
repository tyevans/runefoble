---
id: '0222'
title: Character Roster Styles Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0012
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0222: Character Roster Styles Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/character_sheet/ui/src/roster/runefoble-character-roster.styles.ts` (344 lines, 68.8% of limit) into modular CSS modules under `services/character_sheet/ui/src/roster/styles/` (`roster_layout.styles.ts`, `character_card.styles.ts`, `assignment_dialog.styles.ts`), ensuring all style modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/character_sheet/ui/src/roster/runefoble-character-roster.styles.ts` has grown to 344 lines as character cards, roster grids, campaign assignment dialogs, and action buttons are authored in a monolithic style file. As additional character builder interactions and sheet filters are added, this file will approach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Modular CSS composition with Lit `css` tagged templates.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Bauhaus design token usage and high-contrast styling invariants.

## Scope of Work
1. **Style Module Decomposition (`services/character_sheet/ui/src/roster/styles/`)**:
   - `roster_layout.styles.ts`: Host container, grid layouts, header, search bar, and primary action buttons (< 110 lines).
   - `character_card.styles.ts`: Character card elevation, vitals badges, class tags, and token portrait thumbnail (< 120 lines).
   - `assignment_dialog.styles.ts`: Campaign assignment modal, party slots, confirmation controls, and empty state (< 120 lines).
2. **Aggregator Export (`runefoble-character-roster.styles.ts`)**:
   - Compose the modular styles into `characterRosterStyles = [rosterLayoutStyles, characterCardStyles, assignmentDialogStyles]` (< 40 lines).
3. **Verification**:
   - Verify all Storybook stories in `services/character_sheet/ui/src/roster/` render and pass tests.

## Definition of Done
- `runefoble-character-roster.styles.ts` reduced to < 50 lines.
- All extracted style modules under `services/character_sheet/ui/src/roster/styles/` strictly < 130 lines.
- Storybook stories for `<runefoble-character-roster>` pass and visual layout is preserved.
- Code passes lint and typecheck.
