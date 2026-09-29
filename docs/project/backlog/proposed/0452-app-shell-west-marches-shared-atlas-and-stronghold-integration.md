---
id: '0452'
title: App Shell West Marches Shared Atlas and Stronghold Integration
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0135
- TASK-0250
- TASK-0451
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0018
- PRD-0023
governing_stories:
- US-0058
- US-0050
- US-0067
target_release: 0.9.0
---

# TASK-0452: App Shell West Marches Shared Atlas and Stronghold Integration

## Status
Proposed

## Summary
Integrate the `<runefoble-west-marches-atlas>` component into the App Shell campaign hub (`frontend/src/runefoble-app.ts`), add route `#/campaigns/:campaignId/frontier` to `STANDARD_ROUTES` and breadcrumbs in `frontend/src/router/router.ts`, add West Marches client methods to `frontend/src/services/app-data-service.ts`, and bind `@place-pin`, `@filter-pins`, and `@upgrade-stronghold` events to synchronize cross-campaign frontier discoveries and communal haven upgrades.

## Problem Statement
The `<runefoble-west-marches-atlas>` component is implemented in `@runefoble/campaign-lore-ui`, featuring interactive hex-grid coordinate snapping, multi-party discovery pins with party credit badges, regional outpost markers, and communal stronghold facility upgrade cards per PRD-0018 and US-0058. However, the component is not registered or rendered within the unified App Shell. Players and DMs navigating campaigns cannot inspect their shared West Marches frontier, log new discoveries, or co-fund stronghold upgrades from the web application interface.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Web Component encapsulation with CustomEvent message passing across Shadow DOM.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast geometric map pins, faction badges, and themed stronghold status bars.
- **ADR-0013: Frontend Microfrontend Architecture**: Bounded context UI integration into the centralized App Shell.

## Product & User Story References
- [`prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md`](../../product/accepted/prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)
- [`us-0050-collaborative-campaign-atlas-and-living-codex.md`](../../user_stories/accepted/us-0050-collaborative-campaign-atlas-and-living-codex.md)
- [`us-0067-campaign-detail-view-orchestration.md`](../../user_stories/accepted/us-0067-campaign-detail-view-orchestration.md)

## Scope of Work
1. **Client Router & Navigation (`frontend/src/router/router.ts`)**:
   - Register route `#/campaigns/:campaignId/frontier` in `STANDARD_ROUTES`.
   - Update breadcrumb resolution to include `Frontier Atlas` with proper hierarchical parent linking.
   - Add tab entry to `<runefoble-campaign-nav>` linking to `#/campaigns/${campaignId}/frontier`.
2. **App Data Service Extension (`frontend/src/services/app-data-service.ts`)**:
   - Add `fetchWestMarchesOverview(universeId: string): Promise<WestMarchesOverview>` (< 30 lines).
   - Add `submitDiscoveryPin(universeId: string, pin: NewDiscoveryPin): Promise<WestMarchesDiscovery>` (< 30 lines).
   - Add `contributeStrongholdUpgrade(universeId: string, facilityId: string, goldAmount: number): Promise<StrongholdUpgradeResult>` (< 30 lines).
   - Provide realistic offline fixtures in `app-data-service.fixtures.ts` for local development.
3. **App Shell View Composition (`frontend/src/runefoble-app.ts`)**:
   - Import `<runefoble-west-marches-atlas>` and mount when active route matches `#/campaigns/:campaignId/frontier`.
   - Handle `@place-pin` event: invoke `appDataService.submitDiscoveryPin()` and dispatch toast notification.
   - Handle `@upgrade-stronghold` event: invoke `appDataService.contributeStrongholdUpgrade()` and refresh communal haven status.
4. **Verification**:
   - Add unit/component tests in `frontend/test/` asserting route navigation, component mounting, pin submission, and stronghold upgrade event handling.

## Definition of Done
1. Route `#/campaigns/:campaignId/frontier` deep-links directly to `<runefoble-west-marches-atlas>`.
2. Campaign navigation tab bar includes link to Frontier Atlas with active highlighting.
3. Discovery pins and stronghold contributions dispatch API calls through `appDataService`.
4. All TypeScript tests pass (`npm test`).
5. All modified files adhere to Hard Invariant 6 (< 500 lines).
