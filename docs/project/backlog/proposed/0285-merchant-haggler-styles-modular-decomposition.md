---
id: '0285'
title: Merchant Haggler Styles Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0262
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0075
target_release: 0.8.0
---

# TASK-0285: Merchant Haggler Styles Modular Decomposition

## Status
Proposed

## Summary
Decompose `frontend/src/components/minigames/runefoble-merchant-haggler.styles.ts` (311 lines, 62.2% of limit) into modular CSS submodules under `frontend/src/components/minigames/styles/` (`haggler-base.styles.ts`, `haggler-meters.styles.ts`, `haggler-rhetoric.styles.ts`, `haggler-dm-controls.styles.ts`), ensuring all style modules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`runefoble-merchant-haggler.styles.ts` defines base layout styling, merchant mood and patience meter animations, rhetoric move button state grids, dialogue log speech bubbles, and DM live price arbitration panels in a single 311-line file. As multi-currency exchange rates and multi-item bundle inspection drawers are styled, this file will expand towards the 500-line invariant limit unless modularized.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook Design System**: Component style composability and CSS template literal structure.
- **ADR-0012: Bauhaus Theme and Design Tokens**: Design token variables, high-contrast borders, and geometric hard drop shadows.
- **ADR-0013: Frontend Microfrontend Architecture**: Clean scoped styling per component submodule.

## Scope of Work
1. **Base & Layout Styles (`frontend/src/components/minigames/styles/haggler-base.styles.ts`)**:
   - Extract host container, header, merchant avatar, and dialogue speech bubbles (< 90 lines).
2. **Meter & Barter Animation Styles (`frontend/src/components/minigames/styles/haggler-meters.styles.ts`)**:
   - Extract price tug-of-war meter, patience bar, and mood indicator styling (< 80 lines).
3. **Rhetoric & Tactic Styles (`frontend/src/components/minigames/styles/haggler-rhetoric.styles.ts`)**:
   - Extract persuasive tactic buttons, counter-offer controls, and walk-away action styles (< 80 lines).
4. **DM Controls & Live Arbitration (`frontend/src/components/minigames/styles/haggler-dm-controls.styles.ts`)**:
   - Extract DM secret intervention drawer, mood adjustment sliders, and one-click deal veto/accept buttons (< 80 lines).
5. **Aggregator & Export**:
   - Update `runefoble-merchant-haggler.styles.ts` to compose and export modular CSS arrays (< 30 lines).

## Definition of Done
- `frontend/src/components/minigames/styles/` submodules strictly < 110 lines each.
- `runefoble-merchant-haggler.styles.ts` aggregator strictly < 30 lines.
- Passes all component tests and visual verification via Storybook.
- Code passes `npm run lint` and TypeScript typechecks.
