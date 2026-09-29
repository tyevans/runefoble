---
id: '0504'
title: Tactile Board Spoken Ghost Preview Interactive Fine-Tuning and Confirmation
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0084
- TASK-0125
- TASK-0188
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0013
governing_stories:
- US-0043
- US-0056
target_release: 0.9.0
---

# TASK-0504: Tactile Board Spoken Ghost Preview Interactive Fine-Tuning and Confirmation

## Status
Proposed

## Summary
Extend `<runefoble-board>` ghost preview subsystem (`services/board_state/ui/src/ghost_preview.ts`) with interactive touch and pointer controls allowing players and DMs to drag-adjust the proposed destination, fine-tune target reticles, and execute or dismiss pending spoken intent mutations via floating confirmation action badges (`Execute`, `Adjust`, `Dismiss`) before persisting changes to the game session state.

## Problem Statement
When a player speaks a natural language command (e.g. "I move behind the pillar and cast Guiding Bolt at the skeleton"), The Watcher generates a ghost preview indicating proposed target coordinates within 200ms. However, speech parsing can occasionally target an adjacent grid cell or wrong monster when names or coordinates are ambiguous. Currently, players have no tactile way to nudge the ghost token to the intended cell or cancel the action before it executes into persistent domain state, creating frustration and requiring manual DM rollbacks.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Interactive micro-interactions encapsulated in Shadow DOM with CustomEvents.
- **ADR-0012: CSS Custom Properties & Bauhaus Design Tokens**: Floating action badges adhere to 44x44px minimum touch targets and Bauhaus geometric styling.
- **ADR-0013: Frontend Microfrontend Architecture**: Ghost preview events (`@ghost-preview-confirmed`, `@ghost-preview-cancelled`, `@ghost-preview-adjusted`) dispatch to owning container.

## Product & User Story References
- [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
- [`us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md`](../../user_stories/accepted/us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md)

## Scope of Work
1. **Interactive Ghost Drag Handles (`services/board_state/ui/src/ghost_preview.ts`)**:
   - Allow clicking/dragging the semi-transparent ghost preview token to adjacent grid cells with tactile path recalculation.
   - Update step counter and terrain movement cost dynamically as the ghost destination is adjusted.
2. **Floating Confirmation Action Badge (`services/board_state/ui/src/ghost_confirmation_badge.ts`)**:
   - Render a compact Bauhaus floating badge adjacent to the ghost token displaying:
     - `Confirm` (Checkmark icon / keyboard Enter): Emits `@ghost-preview-confirmed` with final `(x, y)` coordinates and action payload.
     - `Dismiss` (Cross icon / keyboard Escape): Emits `@ghost-preview-cancelled` and clears preview layer.
   - Enforce 44x44px touch targets for tablet ergonomics.
3. **Board Integration & Storybook Verification**:
   - Bind keyboard shortcuts (`Enter` to confirm, `Esc` to dismiss) and pointer events to ghost state.
   - Author Storybook stories illustrating interactive ghost adjustment and floating badge actions.

## Definition of Done
1. Dragging a ghost preview token nudges destination coordinates with instantaneous trajectory recalculation.
2. Floating confirmation badge renders with accessible touch targets and triggers `@ghost-preview-confirmed` or `@ghost-preview-cancelled`.
3. Storybook stories demonstrate interactive adjustment flow with full keyboard navigation support.
4. Component passes TypeScript checks (`npm run check`) and unit test coverage.
