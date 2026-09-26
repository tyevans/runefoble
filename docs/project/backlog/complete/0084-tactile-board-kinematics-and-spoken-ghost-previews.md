---
id: 0084
title: Tactile Board Kinematics and Spoken Ghost Previews
status: Complete
created: 2026-09-26
dependencies:
- TASK-0004
- TASK-0010
- TASK-0039
- TASK-0072
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/34
---
# TASK-0084: Tactile Board Kinematics and Spoken Ghost Previews

## Status
Refined

## Summary
Enhance the tactical board microfrontend (`services/board_state/ui/src/runefoble-board.ts`) with tactile token kinematics (subtle inertia, spring dampening, snap-to-grid collision, and interactive route distance measuring in 5-foot increments), paired with sub-200ms real-time semi-transparent "ghost previews" of spoken action intents before committing changes to the persistent game state.

## Problem Statement
Per PRD-0013 and US-0043, tabletop players and Dungeon Masters currently experience disconnected interactions:
1. Spoken voice commands ("Valeros moves 3 squares north and attacks the Orc") commit immediately or fail silently without a visual staging verification on the board.
2. Token drag-and-drop lacks physical presence and tactile feedback, feeling like a flat coordinate form rather than moving a miniature on a physical battlemat.
3. Path distance and terrain penalties (difficult terrain, hazard zones) are difficult to gauge on the fly without manual calculation.

## INVEST Criteria Evaluation
- **Independent (I)**: Enhances presentation and interaction in `services/board_state/ui/` with WebSocket event preview hooks without breaking existing event sourcing or backend persistence.
- **Negotiable (N)**: Kinematic easing curves and ghost styling (opacity, dashed targeting vector lines) can be styled with Bauhaus design tokens.
- **Valuable (V)**: Fulfills the core product vision: "Speak and the board obeys" with visual intent confirmation and tactile delight.
- **Estimable (E)**: Built on existing Lit Web Components, HTML5 Canvas/SVG, and WebSocket client subscriptions.
- **Small (S)**: Scope strictly isolated to `services/board_state/ui/` and its Storybook stories.
- **Testable (T)**: Storybook stories verify visual states, and blackbox tests verify WebSocket preview messaging and commitment flow.

## Governing Architecture & ADRs
- **ADR-0004**: Lit Web Components and Storybook UI (Shadow DOM, reactive state).
- **ADR-0012**: Design System Theming Tokens & Bauhaus Modernist Aesthetic.
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring.
- **PRD-0013**: Immersive & Intuitive Frontend Experience with Tactile Board Kinematics.
- **US-0043**: Tactile Kinetic Board Interaction and Spoken Ghost Previews.

## Key Changes & Specifications
1. **Kinematic Token Dragging & Route Measuring (`services/board_state/ui/src/runefoble-board.ts`)**:
   - Implement inertial spring-damped drag kinematics with snap-to-grid collision.
   - Dynamic waypoint distance ruler displaying cumulative travel in 5-ft increments during dragging.
   - Automatic visual highlights for difficult terrain (+5ft movement penalty) and hazard squares along the trajectory.
2. **Spoken Ghost Preview Engine (`services/board_state/ui/src/ghost_preview.ts`)**:
   - Receive `SpeechIntentParsed` / WebSocket intent previews within 200ms of speech resolution.
   - Render a semi-transparent ghost token (50% opacity, pulsing Bauhaus accent ring) at the target coordinates.
   - Render an animated dashed targeting vector line from source to target.
   - Tap/click ghost or invoke "Confirm" action to commit movement; dismiss or timeout to discard.
3. **Storybook Verification (`services/board_state/ui/src/stories/runefoble-board.stories.ts`)**:
   - Story 1: Token kinematics with path measurement and terrain highlight.
   - Story 2: Spoken ghost preview with interactive confirmation tap.
   - Story 3: Ghost cancellation and timeout rollback.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Component Enhancement**:
   - Ghost preview rendering and kinematic drag handlers implemented in `services/board_state/ui/`.
   - Ghost token renders within 200ms upon receiving preview intent over WebSocket frontdoor.
2. **Storybook Verification**:
   - Interactive stories running cleanly with zero console errors.
3. **Frontdoor Blackbox Verification**:
   - Blackbox tests in `tests/test_blackbox_board_sync.py` or `tests/test_blackbox_ghost_previews.py` verify preview message handling and confirmation flow.
4. **File Length Compliance**:
   - All touched files strictly < 500 lines per Hard Invariant 6.
5. **Quality Gates**:
   - Frontend passes `pnpm run build` and Python passes `uv run pytest`.
