---
id: '0513'
title: App Shell Campaign Town Haven Route and View Orchestration
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0206
- TASK-0250
- TASK-0259
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
- PRD-0024
governing_stories:
- US-0066
- US-0067
- US-0072
- US-0076
target_release: 0.9.0
---

# TASK-0513: App Shell Campaign Town Haven Route and View Orchestration

## Status
Proposed

## Summary
Integrate the deep-linkable settlement route `#/campaigns/:campaignId/town` into the client SPA router, add dynamic breadcrumbs, introduce the "Town Haven" tab in the campaign hub navigation, and orchestrate settlement data fetching (havens, establishments, civic notices) in the Lit App Shell per PRD-0024 and ADR-0004.

## Problem Statement
While the domain aggregates for settlement havens, NPC workers, and civic bulletin boards were implemented in TASK-0259 through TASK-0263, the client application shell lacks a designated route and view for settlements. Players and DMs navigating campaign sections can access Overview, Party Characters, Codex, and Analytics, but cannot navigate to `#/campaigns/:id/town` to inspect or manage their communal settlement havens from the main application shell.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Component-based UI orchestration in the App Shell.
- **ADR-0012: Theme Management and Bauhaus Design Tokens**: High-contrast theme token inheritance and responsive layouts.
- **ADR-0013: Microfrontend Architecture & Modular Decomposition**: Decoupled component composition with Shadow DOM encapsulation.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- [`us-0066-client-side-routing-navigation-and-breadcrumbs.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)
- [`us-0067-campaign-detail-view-and-session-scheduling.md`](../../user_stories/accepted/us-0067-campaign-detail-view-and-session-scheduling.md)
- [`us-0072-mobile-responsive-settlement-browser-and-town-builder.md`](../../user_stories/accepted/us-0072-mobile-responsive-settlement-browser-and-town-builder.md)
- [`us-0076-town-bulletin-board-civic-rumors-and-bounties.md`](../../user_stories/accepted/us-0076-town-bulletin-board-civic-rumors-and-bounties.md)

## Scope of Work
1. **Router Registration (`frontend/src/router/router.ts`)**:
   - Add `#/campaigns/:campaignId/town` to `STANDARD_ROUTES`.
   - Update `generateBreadcrumbs` to produce: `Home > Campaigns > [Campaign Title] > Town Haven`.
2. **Campaign Hub Navigation Tab (`frontend/src/runefoble-app.ts`)**:
   - Update `renderCampaignTabs` to include a "Town Haven" tab navigating to `#/campaigns/${cId}/town`.
   - Support `campaign-town` in `AppActiveView` and `getActiveView()`.
3. **App Shell State & Data Loading**:
   - Add methods in `appDataService` (`fetchSettlementHaven`, `fetchEstablishments`) delegating to gateway endpoints.
   - Load settlement haven and bulletin board state when activating the town view.
4. **View Composition**:
   - Render the settlement haven layout microfrontend and town bulletin board within the campaign view container.
5. **Verification**:
   - Add unit tests in `frontend/test/router.test.ts` and `frontend/test/app_shell.test.ts` asserting route matching, breadcrumbs generation, and tab navigation.

## Definition of Done
1. `#/campaigns/:campaignId/town` is registered in `router.ts` and correctly generates breadcrumbs.
2. The campaign tab bar includes the "Town Haven" tab and responds to click/navigation events.
3. App Shell loads and renders settlement haven data without console errors.
4. All router and App Shell unit tests pass with 100% assertions.
