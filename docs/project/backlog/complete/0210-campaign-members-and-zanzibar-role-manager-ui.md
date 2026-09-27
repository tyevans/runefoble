---
id: '0210'
title: Campaign Members and Zanzibar Role Manager UI
status: Complete
created: 2026-09-27
dependencies:
- TASK-0208
- TASK-0209
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0063
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/200
---
# TASK-0210: Campaign Members and Zanzibar Role Manager UI

## Status
Refined

## Summary
Implement the `<runefoble-campaign-members>` Lit Web Component in `services/game_session/ui/src/campaigns/`, allowing Game Masters to inspect campaign rosters, generate invite links, and assign SpiceDB Zanzibar roles (`dungeon_master`, `player`, `spectator`) directly from the UI.

## Problem Statement
Game Masters cannot manage campaign members or invite friends from the browser UI. Role changes currently require direct database updates or curl commands to SpiceDB endpoints.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/define-spicedb-zanzibar-permissions.md`: Role relations and permission checks for campaigns.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit component standards.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Binding member actions to fine-grained Zanzibar relations.
  - **ADR-0004: Lit Web Components and Storybook UI**: Microfrontend component standards.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Form controls, role badges, and table styling.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Vendored in `@runefoble/game-session-ui`.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Story**: [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)

## Detailed Specification & Implementation Plan
1. **Campaign Members Component (`services/game_session/ui/src/campaigns/runefoble-campaign-members.ts`)**:
   - Display member list with avatars, usernames, assigned characters, and current roles.
   - Role selector dropdown allowing GMs to assign `dungeon_master`, `player`, or `spectator` roles.
   - Remove member button with confirmation dialog.
2. **Invite Link Generator**:
   - "Invite Player" button that generates a copyable share link (`https://.../#/join/:token`) with customizable role pre-assignment.
3. **Storybook Stories**:
   - `services/game_session/ui/src/campaigns/runefoble-campaign-members.stories.ts` showing GM management mode and player view-only mode.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates independently within campaign view tabs, testable with mock member fixtures.
- **Negotiable (N)**: Display format of roles and copyable link style can be adapted.
- **Valuable (V)**: Empowers Game Masters to organize players and enforce Zanzibar access control directly in the browser.
- **Estimable (E)**: Pure Lit Web Component and Storybook stories sized within a single pass.
- **Small (S)**: Component is strictly <250 lines, adhering to Hard Invariant 6.
- **Testable (T)**: Frontdoor component tests verify role change events and invite link copying.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Component implemented in `services/game_session/ui/src/campaigns/runefoble-campaign-members.ts` (<250 lines).
2. Storybook stories pass in all color modes.
3. Registered in `services/game_session/ui/manifest.json`.
4. Adheres to file length invariant (<500 lines).
