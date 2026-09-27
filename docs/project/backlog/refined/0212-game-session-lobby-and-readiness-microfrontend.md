---
id: '0212'
title: Game Session Lobby and Readiness Microfrontend
status: Refined
created: 2026-09-27
dependencies:
- TASK-0208
- TASK-0209
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0065
target_release: 0.8.0
---

# TASK-0212: Game Session Lobby and Readiness Microfrontend

## Status
Refined

## Summary
Implement `<runefoble-session-lobby>` in `services/game_session/ui/src/lobby/`, providing a pre-game staging room where players check in, select their character, toggle readiness, and Game Masters launch the live tabletop session.

## Problem Statement
Sessions currently have no pre-game assembly staging area. Users are thrust directly into a running board state without a mechanism to confirm attendance, assign missing player AI stand-ins, or coordinate game start.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit component standards.
  - `docs/reference/design-tokens-and-themes.md`: High-contrast badge tokens and action buttons.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Standard Lit Web Component.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast readiness badges, toggle switches, and launch button.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Vendored in `@runefoble/game-session-ui`.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Story**: [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)

## Detailed Specification & Implementation Plan
1. **Session Lobby Component (`services/game_session/ui/src/lobby/runefoble-session-lobby.ts`)**:
   - Participant list displaying user avatar, online status, selected character card preview, and readiness badge ("Ready" / "Setting Up").
   - Character selector dropdown allowing players to pick from their owned characters.
   - Absentee / Stand-in toggle: Player or DM can mark a missing participant for AI stand-in takeover.
   - Readiness checkbox: Player toggles "Ready to Play" status.
2. **DM Launch Controls**:
   - For users with DM/Owner permissions, render prominent "Launch Session" action button.
   - Readiness summary indicator (e.g. "3 of 4 Players Ready").
   - Dispatches `@launch-session` event when DM starts the game.
3. **Storybook Stories**:
   - `services/game_session/ui/src/lobby/runefoble-session-lobby.stories.ts` showing player view (unready/ready) and DM view with launch controls.

## INVEST Criteria Evaluation
- **Independent (I)**: Testable in Storybook with mock participant lists and readiness states.
- **Negotiable (N)**: Readiness indicators and absentee warning styles can be customized.
- **Valuable (V)**: Solves game night coordination, preventing chaotic or out-of-sync session launches.
- **Estimable (E)**: Pure Lit Web Component and Storybook stories sized within a single pass.
- **Small (S)**: Component stays under 260 lines, well below the 500-line limit.
- **Testable (T)**: Frontdoor component tests verify readiness toggles, character selection, and launch event dispatching.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Component implemented in `services/game_session/ui/src/lobby/runefoble-session-lobby.ts` (<260 lines).
2. Declared in `services/game_session/ui/manifest.json`.
3. Storybook stories pass in all themes and color modes.
4. Sized for single `agy -p` pass and <500 lines limit.
