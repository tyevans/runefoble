---
id: '0222'
title: Character Roster Styles Modular Decomposition
status: Refined
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
Refined

## Summary
Decompose `services/character_sheet/ui/src/roster/runefoble-character-roster.styles.ts` (343 lines, 68.6% of limit) into modular CSS modules under `services/character_sheet/ui/src/roster/styles/` (`roster_layout.styles.ts`, `character_card.styles.ts`, `assignment_dialog.styles.ts`), ensuring all style modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/character_sheet/ui/src/roster/runefoble-character-roster.styles.ts` has grown to 343 lines as character cards, roster grids, campaign assignment dialogs, and action buttons are authored in a monolithic style file. As additional character builder interactions and sheet filters are added, this file will approach the 500-line limit unless decomposed.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit component CSS patterns and Storybook verification.
  - `docs/reference/design-tokens-and-themes.md`: Bauhaus typography, border radii, and color elevation tokens.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Modular CSS composition with Lit `css` tagged templates.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Bauhaus design token usage and high-contrast styling invariants.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
  - [`us-0064-character-roster-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-and-party-assignment.md)

## Detailed Specification & Implementation Plan
1. **Style Module Decomposition (`services/character_sheet/ui/src/roster/styles/`)**:
   - `roster_layout.styles.ts`: Host container, grid layouts, header, search bar, and primary action buttons (< 110 lines).
   - `character_card.styles.ts`: Character card elevation, vitals badges, class tags, and token portrait thumbnail (< 120 lines).
   - `assignment_dialog.styles.ts`: Campaign assignment modal, party slots, confirmation controls, and empty state (< 120 lines).
2. **Aggregator Export (`runefoble-character-roster.styles.ts`)**:
   - Compose the modular styles into `characterRosterStyles = [rosterLayoutStyles, characterCardStyles, assignmentDialogStyles]` (< 40 lines).
3. **Verification**:
   - Verify all Storybook stories in `services/character_sheet/ui/src/roster/` render and pass tests.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal style decomposition without modifying public component contract or events.
- **Negotiable (N)**: Style sheet naming and token bindings can be tuned.
- **Valuable (V)**: Protects character roster styles from breaching the 500-line invariant limit.
- **Estimable (E)**: Straightforward CSS rule partitioning.
- **Small (S)**: Target files will each be under 120 lines.
- **Testable (T)**: Storybook visual checks and frontend build verify CSS integrity.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `services/character_sheet/ui/src/roster/runefoble-character-roster.styles.ts` reduced to < 50 lines.
2. All extracted style modules under `services/character_sheet/ui/src/roster/styles/` strictly < 130 lines.
3. Storybook stories for `<runefoble-character-roster>` pass and visual layout is preserved.
4. Code passes lint and typecheck (`pnpm run lint` and `pnpm run build`).
