---
id: '0211'
title: Character Roster and Party Assignment Microfrontend
status: Refined
created: 2026-09-27
dependencies:
- TASK-0206
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0064
target_release: 0.8.0
---

# TASK-0211: Character Roster and Party Assignment Microfrontend

## Status
Refined

## Summary
Implement the `<runefoble-character-roster>` and `<runefoble-character-builder-modal>` Lit Web Components in `services/character_sheet/ui/src/roster/`, enabling players to manage their library of characters and assign owned characters to campaign parties.

## Problem Statement
The frontend only renders a single hardcoded character card ("Kyra the Sun Maiden") inside an active session. Players have no way to create their own character, view multiple characters, or choose which character enters a specific campaign.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Character attributes, conditions, and vitals.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Component isolation in Storybook.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Lit Shadow DOM microfrontend.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Character cards, health bars, and modal controls styled with Bauhaus tokens.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Vendored in `@runefoble/character-sheet-ui`.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Story**: [`us-0064-character-roster-management-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-management-and-party-assignment.md)

## Detailed Specification & Implementation Plan
1. **Character Roster View (`services/character_sheet/ui/src/roster/runefoble-character-roster.ts`)**:
   - Grid of character summary cards: portrait, name, class/subclass, level, HP, armor class, and campaign attachment badge.
   - Quick action buttons: "Inspect Sheet", "Assign to Campaign", "Delete".
2. **Character Builder Modal (`services/character_sheet/ui/src/roster/runefoble-character-builder-modal.ts`)**:
   - Form fields: Name, Class, Level, Max HP, Armor Class, Speed, Ability Scores, and Token Portrait selection.
   - Dispatches `@create-character` CustomEvent upon submission.
3. **Party Assignment Dialog**:
   - Modal allowing players to select from their active campaigns and link the chosen character to the campaign party.
4. **Storybook Stories**:
   - Stories in `services/character_sheet/ui/src/roster/*.stories.ts` demonstrating empty roster, populated roster, and builder modal.

## INVEST Criteria Evaluation
- **Independent (I)**: Roster components interact strictly via CustomEvents, testable independently in Storybook.
- **Negotiable (N)**: Form field layouts and character card dimensions can be styled via CSS tokens.
- **Valuable (V)**: Gives players persistent character identity and freedom to create multiple characters across campaigns.
- **Estimable (E)**: Pure Lit Web Components and Storybook stories sized within a single pass.
- **Small (S)**: Both files stay <260 lines, well below the 500-line invariant limit.
- **Testable (T)**: Frontdoor component tests verify form input handling, validation, and party assignment events.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Roster and builder components created in `services/character_sheet/ui/src/roster/` (<260 lines each).
2. Exported and declared in `services/character_sheet/ui/manifest.json`.
3. Storybook stories pass in all themes and color modes.
4. Source files strictly adhere to file length invariant (<500 lines).
