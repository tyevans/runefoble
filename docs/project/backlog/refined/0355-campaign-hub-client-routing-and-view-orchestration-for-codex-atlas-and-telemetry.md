---
id: '0355'
title: Campaign Hub Client Routing and View Orchestration for Codex, Atlas, and Telemetry
status: Refined
created: 2026-09-28
dependencies:
- TASK-0047
- TASK-0048
- TASK-0206
- TASK-0250
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0007
- PRD-0012
- PRD-0023
governing_stories:
- US-0063
- US-0065
- US-0067
- US-0068
target_release: 0.9.0
---

# TASK-0355: Campaign Hub Client Routing and View Orchestration for Codex, Atlas, and Telemetry

## Status
Refined

## Summary
Eradicate disabled, unclickable tabs in the Campaign Hub by registering client routes `#/campaigns/:campaignId/codex` and `#/campaigns/:campaignId/analytics` in `frontend/src/router/router.ts`, importing `@runefoble/campaign-lore-ui` and `@runefoble/campaign-analytics-ui` into `frontend/src/runefoble-app.ts`, removing inline `e.preventDefault()` dead handlers in `renderCampaignTabs()`, and mounting `<runefoble-campaign-atlas>` (with codex sidebar) and `<runefoble-campaign-analytics>` in `renderActiveView()`.

## Problem Statement
In the Campaign Hub (`#/campaigns/:campaignId`), clicking the "Codex & Lore" or "Chronicle & Stats" tabs does nothing because `renderCampaignTabs()` explicitly intercepts clicks with `@click=${(e: Event) => { e.preventDefault(); }}` and uses invalid hash fragments (`href="#/campaigns/${cId}#codex"`). 

In `frontend/src/router/router.ts`, neither `#/campaigns/:campaignId/codex` nor `#/campaigns/:campaignId/analytics` is registered in `STANDARD_ROUTES`. In `frontend/src/runefoble-app.ts`, `AppActiveView` lacks view states for these tabs, `getActiveView()` falls back to `campaign-detail`, and `renderActiveView()` contains no rendering branch to mount the rich components already built in `services/campaign_lore/ui` (`runefoble-campaign-codex`, `runefoble-campaign-atlas`) or `services/campaign_analytics/ui` (`runefoble-campaign-analytics`, `runefoble-combat-heatmap`, `runefoble-chronicle-timeline`).

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: Deep-linkable client SPA routes, breadcrumbs, and view resolution.
  - `docs/how-to/interact-with-campaign-atlas-and-codex.md`: Campaign atlas, milestone pins, territory overlays, and party codex notes.
  - `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md`: Combat telemetry heatmap, encounter MVP awards, and chronicle timeline.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Web component composition in App Shell.
  - **ADR-0007: Domain-Driven Design and Bounded Contexts**: Campaign lore and analytics context boundaries.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Visual consistency across sub-views.
  - **ADR-0013: Frontend Microfrontend Architecture**: Bounded context UI consumption via workspace dependencies.

## Scope of Work & Implementation Plan
1. **Client Router Registration (`frontend/src/router/router.ts`)**:
   - Add `#/campaigns/:campaignId/codex` and `#/campaigns/:campaignId/analytics` to `STANDARD_ROUTES`.
   - Update `generateBreadcrumbs()`:
     - `#/campaigns/:campaignId/codex` -> `[Campaigns, <Campaign Title>, Codex & Atlas]`
     - `#/campaigns/:campaignId/analytics` -> `[Campaigns, <Campaign Title>, Chronicle & Stats]`
2. **App Shell View Model Expansion (`frontend/src/runefoble-app.ts`)**:
   - Import `@runefoble/campaign-lore-ui` and `@runefoble/campaign-analytics-ui`.
   - Expand `AppActiveView` union type:
     ```typescript
     export type AppActiveView = ... | 'campaign-codex' | 'campaign-analytics';
     ```
   - Update `getActiveView()` to check for `/codex` and `/analytics` before the generic `#/campaigns/:campaignId` prefix.
   - Update `loadRouteData()` to fetch campaign title and parameters when visiting codex or analytics sub-routes.
3. **Campaign Navigation Tabs Update (`frontend/src/runefoble-app.ts`)**:
   - In `renderCampaignTabs(activeTab: 'overview' | 'characters' | 'codex' | 'analytics')`:
     - Codex tab: `href="#/campaigns/${cId}/codex"`, `@click=${(e: Event) => { e.preventDefault(); router.navigate('#/campaigns/' + cId + '/codex'); }}`.
     - Analytics tab: `href="#/campaigns/${cId}/analytics"`, `@click=${(e: Event) => { e.preventDefault(); router.navigate('#/campaigns/' + cId + '/analytics'); }}`.
4. **Sub-View Component Mounting (`frontend/src/runefoble-app.ts`)**:
   - In `renderActiveView()`:
     - When `view === 'campaign-codex'`: Render `<runefoble-campaign-atlas .campaignId=${this.campaignId} .isGm=${this.isDM}></runefoble-campaign-atlas>`.
     - When `view === 'campaign-analytics'`: Render `<runefoble-campaign-analytics .campaignId=${this.campaignId} apiBaseUrl=""></runefoble-campaign-analytics>`.
   - Retain `<runefoble-campaign-header>` and `<nav class="campaign-nav-tabs">` across all campaign sub-views for unified navigation.
5. **Gateway Routing / Proxy Alignment (`gateway/api/src/gateway_api/main.py`)**:
   - Ensure routes for `/api/v1/campaigns/{id}/codex`, `/api/v1/campaigns/{id}/atlas`, and `/api/v1/analytics/campaigns/{id}` pass through to respective services or provide mock gateway handlers in offline mode.
6. **Blackbox TDD Tests**:
   - Update `frontend/test/campaign-detail-view.test.ts` and `frontend/test/app-shell.test.ts` to assert that navigating to `#/campaigns/:campaignId/codex` and `#/campaigns/:campaignId/analytics` activates the corresponding tabs, mounts the components, and renders breadcrumbs.

## INVEST Criteria Evaluation
- **Independent (I)**: Implemented as App Shell route and component mounting logic without modifying domain aggregates.
- **Negotiable (N)**: Tab ordering and visual layout can be customized.
- **Valuable (V)**: Removes major dead ends in the UI, unlocking full worldbuilding lore, map exploration, and combat telemetry.
- **Estimable (E)**: Existing components are already built, tested in Storybook, and exported.
- **Small (S)**: Confined to App Shell routing and tab rendering (~100 lines altered in `runefoble-app.ts`).
- **Testable (T)**: Tested with Lit component test runners and browser URL hash navigation assertions.

## Definition of Done
1. Clicking "Codex & Lore" smoothly navigates to `#/campaigns/:campaignId/codex` and displays the campaign atlas and lore codex.
2. Clicking "Chronicle & Stats" smoothly navigates to `#/campaigns/:campaignId/analytics` and displays combat heatmaps, timelines, and MVP metrics.
3. Breadcrumbs correctly reflect the active campaign section.
4. Zero inline `e.preventDefault()` dead handlers remain in campaign navigation.
5. `frontend/src/runefoble-app.ts` file length remains strictly under 400 lines (Hard Invariant 6).
