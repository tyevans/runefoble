---
id: '0453'
title: App Shell Caravan Trading and Bounty Board Integration
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0136
- TASK-0250
- TASK-0451
governing_adrs:
- ADR-0004
- ADR-0006
- ADR-0013
governing_prds:
- PRD-0018
- PRD-0023
governing_stories:
- US-0058
- US-0067
target_release: 0.9.0
---

# TASK-0453: App Shell Caravan Trading and Bounty Board Integration

## Status
Proposed

## Summary
Integrate the `<runefoble-caravan-board>` component into the App Shell campaign hub (`frontend/src/runefoble-app.ts`), register route `#/campaigns/:campaignId/caravans` in `STANDARD_ROUTES` and `frontend/src/router/router.ts`, add caravan trade and mercenary contract API methods to `frontend/src/services/app-data-service.ts`, and bind `@dispatch-caravan`, `@claim-contract`, and `@fulfill-contract` events to real-time WebSocket state updates for cross-campaign trade ledgers and bounty escrow.

## Problem Statement
The `<runefoble-caravan-board>` component in `@runefoble/game-session-ui` renders overland trade routes, transit calendar dates, item manifest manifests, and cross-party mercenary contracts per PRD-0018 and US-0058. However, this component is not integrated into the unified App Shell. Players cannot view active caravan routes, dispatch excess crafting reagents or harvested monster parts to regional hubs, or accept bounty contracts posted by other parties in their West Marches campaign cluster.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated component composition with Bauhaus design tokens.
- **ADR-0006: Event-Driven Architecture with Redis Streams**: Real-time event propagation for caravan departures, arrivals, and contract claims.
- **ADR-0013: Frontend Microfrontend Architecture**: Isolated presentation logic in service bounded contexts integrated via the App Shell.

## Product & User Story References
- [`prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md`](../../product/accepted/prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)
- [`us-0067-campaign-detail-view-orchestration.md`](../../user_stories/accepted/us-0067-campaign-detail-view-orchestration.md)

## Scope of Work
1. **Client Router & Navigation (`frontend/src/router/router.ts`)**:
   - Register route `#/campaigns/:campaignId/caravans` in `STANDARD_ROUTES`.
   - Update breadcrumb resolution to include `Caravan Trading & Bounties`.
   - Add tab entry to `<runefoble-campaign-nav>` linking to `#/campaigns/${campaignId}/caravans`.
2. **App Data Service Extension (`frontend/src/services/app-data-service.ts`)**:
   - Add `fetchCaravanContracts(universeId: string): Promise<CaravanContract[]>` (< 30 lines).
   - Add `postCaravanContract(universeId: string, contract: NewContract): Promise<CaravanContract>` (< 30 lines).
   - Add `claimCaravanContract(contractId: string, campaignId: string): Promise<CaravanContract>` (< 30 lines).
   - Add `dispatchCaravanTrade(payload: DispatchCaravanRequest): Promise<CaravanTransit>` (< 30 lines).
   - Provide realistic offline mock contracts and routes in `app-data-service.fixtures.ts`.
3. **App Shell View Composition (`frontend/src/runefoble-app.ts`)**:
   - Import `<runefoble-caravan-board>` and render when route matches `#/campaigns/:campaignId/caravans`.
   - Handle `@dispatch-caravan`: call `appDataService.dispatchCaravanTrade()` and trigger route refresh.
   - Handle `@claim-contract`: call `appDataService.claimCaravanContract()` and verify gold escrow locks.
   - Handle `@fulfill-contract`: call fulfillment endpoint and update player inventory balance.
4. **Verification**:
   - Add unit/component tests in `frontend/test/` asserting route mounting, event dispatch, and state synchronization.

## Definition of Done
1. Route `#/campaigns/:campaignId/caravans` deep-links directly to `<runefoble-caravan-board>`.
2. Navigation tab bar provides active link to Caravans view with unread contract badges.
3. Caravan dispatches and contract claims execute successfully through `appDataService`.
4. All TypeScript tests pass (`npm test`).
5. All modified files adhere to Hard Invariant 6 (< 500 lines).
