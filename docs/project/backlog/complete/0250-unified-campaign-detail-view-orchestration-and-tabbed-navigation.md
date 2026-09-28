---
id: '0250'
title: Unified Campaign Detail View Orchestration and Tabbed Navigation
status: Complete
created: 2026-09-27
dependencies:
- TASK-0247
- TASK-0248
- TASK-0249
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0064
- US-0066
- US-0067
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/286
---
# TASK-0250: Unified Campaign Detail View Orchestration and Tabbed Navigation

## Status
Refined

## Summary
Refactor the `campaign-detail` view in `frontend/src/runefoble-app.ts` into a cohesive, tabbed campaign command center integrating `<runefoble-campaign-header>`, `<runefoble-campaign-members>`, `<runefoble-session-list>`, and sub-navigation links to the party character roster (`#/campaigns/:id/characters`), campaign lore codex, and chronicle analytics.

## Problem Statement
The current `campaign-detail` view is a rudimentary `div` holding two disconnected components. The app does not call `appDataService.fetchCampaign(campaignId)` when entering the route, leaving `this.campaignTitle` to fall back to raw strings. Furthermore, route `#/campaigns/:campaignId/characters` collides with `campaign-detail` in `getActiveView()`, preventing players from viewing or managing campaign party character assignments.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md`: View orchestration in Lit App Shell.
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: Sub-routing and breadcrumb hierarchy.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: App shell component composition.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Tabbed navigation styling and surface contrast.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Composing decoupled `@runefoble/*-ui` microfrontends.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Stories**:
  - [`us-0064-character-roster-management-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-management-and-party-assignment.md)
  - [`us-0067-campaign-detail-view-and-session-scheduling.md`](../../user_stories/accepted/us-0067-campaign-detail-view-and-session-scheduling.md)

## Detailed Specification & Implementation Plan
1. **Route State & Data Loading (`frontend/src/runefoble-app.ts`)**:
   - In `loadRouteData`, fetch full campaign metadata via `appDataService.fetchCampaign(cId)`.
   - Update `this.campaignTitle` and campaign record state from the fetched record.
2. **Sub-View Disambiguation in `getActiveView()`**:
   - Distinguish `#/campaigns/:campaignId/characters` as view `'campaign-characters'` (rendering `<runefoble-character-roster>` scoped to the active campaign).
   - Distinguish `#/profile` as view `'profile'`.
3. **Tabbed Navigation Bar**:
   - Tabs: `Overview & Sessions` (`#/campaigns/:id`), `Party Characters` (`#/campaigns/:id/characters`), `Codex & Lore`, `Chronicle & Stats`.
   - Bauhaus-styled tab bar adhering to `--rf-border-color` and `--rf-accent-primary`.
4. **Campaign Update Handling**:
   - Listen for `@update-campaign` from header, call `appDataService.updateCampaign`, and refresh view data seamlessly.
5. **Frontdoor Blackbox Verification (`tests/test_blackbox_campaign_detail_view.py`)**:
   - Verify tab navigation, subview rendering, and campaign header data binding via frontdoors.

## INVEST Criteria Evaluation
- **Independent (I)**: Composes ready components into the App Shell router hierarchy.
- **Negotiable (N)**: Tab ordering and external lore deep links can be refined.
- **Valuable (V)**: Elevates the campaign page from a fragmented stub into a unified command hub.
- **Estimable (E)**: Pure Lit template refactoring and route matching adjustments sized for a single pass.
- **Small (S)**: Preserves file length invariant in `runefoble-app.ts` (<450 lines).
- **Testable (T)**: Frontdoor component tests verify view rendering on tab transitions and data loading.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `runefoble-app.ts` loads campaign metadata and renders `<runefoble-campaign-header>`.
2. Navigation between campaign tabs switches subviews without page reloads.
3. `#/campaigns/:id/characters` mounts party character roster with campaign filter applied.
4. Frontdoor blackbox test suite passes via `uv run pytest tests/test_blackbox_campaign_detail_view.py`.
5. `runefoble-app.ts` remains strictly under 450 lines (Hard Invariant 6).
