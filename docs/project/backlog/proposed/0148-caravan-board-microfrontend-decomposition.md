---
id: '0148'
title: Caravan Board Microfrontend Styles and Component Decomposition
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0136
governing_adrs:
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0007
governing_stories:
- US-0058
target_release: 0.5.0
---

# TASK-0148: Caravan Board Microfrontend Styles and Component Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/ui/src/runefoble-caravan-board.ts` (398 lines) and `runefoble-caravan-board.styles.ts` (397 lines) into smaller, focused sub-components and style modules under `services/game_session/ui/src/caravan/` (`contract_card.ts`, `dispatch_modal.ts`, `board_filters.ts`), keeping all UI files < 150 lines per Hard Invariant 6.

## Problem Statement
Both the component logic and CSS styles of `runefoble-caravan-board` are approaching 400 lines (80% of limit). As new filter controls for hazard risks and cross-campaign reputation tags are introduced, decomposing them into atomic custom elements prevents future invariant breaches.

## Governing Architecture & ADRs
- **ADR-0012: Theming System and Accessibility Contrast Invariants**: Atomic style isolation and Bauhaus tokens.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Lit Web Component encapsulation.

## Scope of Work
1. **Contract Card Sub-Component (`services/game_session/ui/src/caravan/contract_card.ts`)**:
   - Extract individual notice board contract card rendering and reward badges (< 120 lines).
2. **Dispatch Modal Sub-Component (`services/game_session/ui/src/caravan/dispatch_modal.ts`)**:
   - Extract escort party assignment and caravan dispatch modal dialog (< 130 lines).
3. **Styles Decomposition (`services/game_session/ui/src/caravan/styles/`)**:
   - Split styling into `board_layout.styles.ts` and `contract_card.styles.ts` (< 120 lines each).
4. **Verification**:
   - Storybook stories and microfrontend manifest continue to render without visual regression.
