---
id: '0213'
title: App Shell View Orchestration and Session Transition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0206
- TASK-0207
- TASK-0209
- TASK-0210
- TASK-0211
- TASK-0212
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0065
- US-0066
target_release: 0.8.0
---

# TASK-0213: App Shell View Orchestration and Session Transition

## Status
Refined

## Summary
Refactor `frontend/src/runefoble-app.ts` to transition from the monolithic, hardcoded demo sandbox into a dynamic multi-view application shell orchestrated by the client router, dynamically mounting Auth, Campaign Dashboard, Character Roster, Session Lobby, and Active VTT views while managing route-aware WebSocket lifecycles.

## Problem Statement
`runefoble-app.ts` currently mounts a single hardcoded session (`sessionId="session-tomb-14"`, `campaignId="4"`) with hardcoded tokens and watcher feed events. It does not respond to route transitions, does not orchestrate campaign or lobby views, and opens WebSocket connections regardless of the user's intent.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/reference/design-tokens-and-themes.md`: Global app shell layout and theme tokens.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Component composition in the app shell.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: App Shell component orchestration.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Preserving global theme tokens across all view transitions.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Composing decoupled `@runefoble/*-ui` microfrontends into the host App Shell.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Story**: [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)
- **User Story**: [`us-0066-client-side-routing-navigation-and-breadcrumbs.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)

## Detailed Specification & Implementation Plan
1. **Dynamic View Rendering in `frontend/src/runefoble-app.ts`**:
   - Bind App Shell to router state (`currentRoute`, `routeParams`).
   - Switch active subview based on route:
     - `login`: Render `<runefoble-auth-modal>`
     - `campaigns`: Render `<runefoble-campaign-dashboard>`
     - `campaign-detail`: Render `<runefoble-campaign-members>` and session list
     - `characters`: Render `<runefoble-character-roster>`
     - `session-lobby`: Render `<runefoble-session-lobby>`
     - `session-active`: Render tactical board, character sheet, watcher feed, and voice controls.
2. **Route-Bound WebSocket Lifecycle**:
   - Establish session WebSocket connection only when entering `session-active` or `session-lobby` routes.
   - Cleanly disconnect and tear down socket listeners when navigating away from active sessions.
3. **Session Start Transition**:
   - Listen for `@launch-session` event or incoming WebSocket `session_started` message and automatically navigate the router from `#/campaigns/:id/lobby/:sessionId` to `#/campaigns/:id/sessions/:sessionId`.

## INVEST Criteria Evaluation
- **Independent (I)**: Composes already-refined microfrontends into view slots without modifying underlying microservices.
- **Negotiable (N)**: Fallback views and transition animations can be configured.
- **Valuable (V)**: Elevates the frontend from a toy demo into a real, functional multi-view platform.
- **Estimable (E)**: Sized for a focused App Shell refactoring pass under 450 lines.
- **Small (S)**: Kept strictly under 450 lines, adhering to Hard Invariant 6 (<500 lines).
- **Testable (T)**: Frontdoor component tests verify view switching on route change events and socket lifecycle cleanup.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `runefoble-app.ts` refactored to mount routed views dynamically.
2. Monolithic mock data removed in favor of route-parameterized service fetching.
3. WebSocket connects and disconnects strictly aligned with session routes.
4. Source file strictly kept under 450 lines (Hard Invariant 6).
