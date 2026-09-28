---
id: '0274'
title: Settlement Bulletin Board Styles Modular Decomposition
status: Refined
created: 2026-09-28
dependencies:
- TASK-0263
governing_adrs:
- ADR-0004
- ADR-0012
governing_prds:
- PRD-0024
governing_stories:
- US-0076
target_release: 0.8.0
---

# TASK-0274: Settlement Bulletin Board Styles Modular Decomposition

## Status
Refined

## Summary
Decompose `frontend/src/components/runefoble-bulletin-board.styles.ts` (384 lines, 76.8% of limit) into focused style modules (`bulletin-board-layout.styles.ts`, `bulletin-board-card.styles.ts`, `bulletin-board-dialog.styles.ts`) under `frontend/src/styles/` or as colocated style modules, reducing each file to < 140 lines per Hard Invariant 6.

## Problem Statement
`frontend/src/components/runefoble-bulletin-board.styles.ts` embeds 384 lines of CSS including corkboard textured grid layout, parchment card styles, wax seal badges, cipher puzzle overlays, bounty reward ribbons, and filter tabs. As mobile-specific gesture targets and responsive card layouts are expanded, this styles file will rapidly breach the 500-line invariant limit unless decoupled into focused sub-sheets.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/develop-lit-components-in-storybook.md`: Component style separation in Lit and Storybook stories.
  - `docs/reference/design-tokens-and-themes.md`: Bauhaus dialog, form input, and elevation tokens.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Component style modularity and Bauhaus token integration.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Form input contrast, parchment textures, and modal overlays.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0024-settlement-haven-builder-and-establishment-ecosystem.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-establishment-ecosystem.md)
  - [`us-0076-town-bulletin-board-and-civic-proclamations.md`](../../user_stories/accepted/us-0076-town-bulletin-board-and-civic-proclamations.md)

## Detailed Specification & Implementation Plan
1. **Layout & Board Styles Extraction (`frontend/src/styles/bulletin-board-layout.styles.ts`)**:
   - Extract corkboard container, responsive grid layout, category tabs, and header action controls (< 130 lines).
2. **Notice Card Styles Extraction (`frontend/src/styles/bulletin-board-card.styles.ts`)**:
   - Extract parchment notice cards, wax seals, cipher runes, torn paper edges, and bounty ribbons (< 140 lines).
3. **Dialog & Form Styles Extraction (`frontend/src/styles/bulletin-board-dialog.styles.ts`)**:
   - Extract notice authoring dialog, cipher puzzle inspection overlay, and action button styles (< 130 lines).
4. **Aggregator Module (`frontend/src/components/runefoble-bulletin-board.styles.ts`)**:
   - Re-export or compose the modular sheets into `bulletinBoardStyles` array (< 30 lines).
5. **Verification**:
   - Verify Storybook stories for `<runefoble-bulletin-board>` render identically across themes.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal style decomposition without modifying public component contract or events.
- **Negotiable (N)**: Style sheet naming and token bindings can be tuned.
- **Valuable (V)**: Protects bulletin board styles from breaching the 500-line invariant limit.
- **Estimable (E)**: Straightforward CSS rule partitioning.
- **Small (S)**: Target files will each be under 140 lines.
- **Testable (T)**: Storybook visual checks and frontend build verify CSS integrity.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `frontend/src/components/runefoble-bulletin-board.styles.ts` reduced to < 40 lines.
2. Extracted CSS modules strictly < 150 lines each per Hard Invariant 6.
3. Storybook stories for bulletin board pass without visual regression.
4. Code passes lint and typecheck (`pnpm run lint` and `pnpm run build`).
