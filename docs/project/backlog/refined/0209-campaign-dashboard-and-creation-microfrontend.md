---
id: '0209'
title: Campaign Dashboard and Creation Microfrontend
status: Refined
created: 2026-09-27
dependencies:
- TASK-0206
- TASK-0208
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0063
target_release: 0.8.0
---

# TASK-0209: Campaign Dashboard and Creation Microfrontend

## Status
Refined

## Summary
Build the `<runefoble-campaign-dashboard>` and `<runefoble-campaign-creator>` Lit Web Components in `services/game_session/ui/src/campaigns/`, providing an interactive campaign grid with status badges, search/filter, and a step-by-step campaign creation wizard.

## Problem Statement
Game Masters and players currently have no visual dashboard to browse available campaigns, inspect active campaign statuses, or launch new campaigns from the frontend.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit component standards, story co-location, and manifest declarations.
  - `docs/reference/design-tokens-and-themes.md`: Bauhaus card tokens, elevation shadows, and status badges.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Shadow DOM components with typed properties.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast card grids, bold borders, offset drop-shadows, and primary color badges.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Vendored in `@runefoble/game-session-ui`.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Story**: [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)

## Detailed Specification & Implementation Plan
1. **Campaign Dashboard Component (`services/game_session/ui/src/campaigns/runefoble-campaign-dashboard.ts`)**:
   - Render responsive Bauhaus grid of campaign cards.
   - Display title, description, DM name, player count, and active session badge ("● Session Live").
   - Filter by role ("All", "DMing", "Playing") and text search.
   - Emits `@select-campaign` event when a user clicks a campaign card.
2. **Campaign Creator Dialog (`services/game_session/ui/src/campaigns/runefoble-campaign-creator.ts`)**:
   - Modal form for creating a campaign: title, setting synopsis, ruleset selection (e.g. SRD 5e), and optional cover art URL.
   - Dispatches `@create-campaign` event upon submission.
3. **Storybook Stories**:
   - Stories for empty dashboard, populated dashboard with mixed roles, and campaign creator dialog in `services/game_session/ui/src/campaigns/*.stories.ts`.

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes standard properties and emits CustomEvents, testable in isolation in Storybook.
- **Negotiable (N)**: Card layout and filter chips can be customized.
- **Valuable (V)**: Provides the central landing hub for users to select, manage, and create tabletop campaigns.
- **Estimable (E)**: Pure Lit Web Components and Storybook stories sized within a single pass.
- **Small (S)**: Dashboard (<280 lines) and creator (<240 lines) stay strictly below 500 lines per file.
- **Testable (T)**: Frontdoor component tests verify card filtering, creation submission, and event dispatching.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Dashboard and creator components authored in `services/game_session/ui/src/campaigns/` (<280 lines each).
2. Registered in `services/game_session/ui/manifest.json`.
3. Storybook stories render without errors in both Dark and Light modes.
4. Exported from `@runefoble/game-session-ui`.
