---
id: '0257'
title: Profile Settings View and Campaign Creation Idempotency
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0206
- TASK-0209
- TASK-0213
governing_adrs:
- ADR-0001
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0062
- US-0070
- US-0071
target_release: 0.8.0
---
# TASK-0257: Profile Settings View and Campaign Creation Idempotency

## Status
Proposed

## Summary
Implement the user profile view (`#/profile`) in `frontend/src/runefoble-app.ts` to resolve the no-op when clicking "Account Settings" in the user menu. Fix the campaign creation bug where a newly created campaign appears twice in the dashboard list by stopping duplicate event propagation in `RunefobleCampaignDashboard` / `RunefobleCampaignCreator` and enforcing ID de-duplication in `AppDataService`.

## Problem Statement
Two critical frontend navigation and data flow defects currently degrade user experience:
1. **Account Settings No-Op**: Clicking "Account Settings" in `runefoble-user-menu` routes to `#/profile`, but `getActiveView()` has no pattern for `#/profile` and falls through to `'campaigns'`. The user remains stuck on the dashboard.
2. **Duplicate Campaign Listing**: When a campaign is submitted via `<runefoble-campaign-creator>`, the modal dispatches a bubbling composed `create-campaign` event. The parent `<runefoble-campaign-dashboard>` captures this and dispatches a second `create-campaign` event without stopping propagation. The shell handles both events and triggers two creation calls, rendering duplicate campaign cards.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/authenticate-with-zitadel-oidc.md`: Profile claims and user info endpoints.
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: SPA route registration and view rendering.
  - `docs/reference/ports-and-endpoints.md`: `GET /api/v1/profile` endpoint definition.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: User identity verification.
  - **ADR-0013: Frontend Microfrontend Architecture**: Event bubbling containment.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Stories**:
  - [`us-0062-user-registration-zitadel-auth-and-profile.md`](../../user_stories/accepted/us-0062-user-registration-zitadel-auth-and-profile.md)
  - [`us-0070-user-account-settings-and-profile-management.md`](../../user_stories/accepted/us-0070-user-account-settings-and-profile-management.md)
  - [`us-0071-campaign-dashboard-idempotency-and-lifecycle.md`](../../user_stories/accepted/us-0071-campaign-dashboard-idempotency-and-lifecycle.md)

## Detailed Specification & Implementation Plan
1. **Profile View Component (`frontend/src/components/runefoble-user-profile.ts`)**:
   - Create Lit Web Component rendering user profile claims (`user_id`, `username`, `email`, `roles`, `is_admin`) retrieved from `GET /api/v1/profile`.
   - Include role badges, current theme / color mode display, and session logout trigger.
2. **App Shell Profile Route (`frontend/src/runefoble-app.ts`)**:
   - Add `'profile'` to `AppActiveView`.
   - In `getActiveView()`, return `'profile'` when `pat === '#/profile'`.
   - In `renderActiveView()`, mount `<runefoble-user-profile>`.
3. **Event Propagation & Idempotency Fix**:
   - In `services/game_session/ui/src/campaigns/runefoble-campaign-dashboard.ts`:
     - In `handleCreatorSubmit(e: CustomEvent)`, call `e.stopPropagation()`.
   - In `frontend/src/services/app-data-service.ts`:
     - In `fetchCampaigns()` and `createCampaign()`, ensure `FALLBACK_CAMPAIGNS` de-duplicates entries by `id` using a `Map<string, CampaignItem>`.

## Definition of Done
- [ ] Clicking "Account Settings" navigates to `#/profile` and mounts the user profile view.
- [ ] User claims (username, email, roles) display cleanly in high-contrast Bauhaus cards.
- [ ] Creating a campaign submits exactly once and lists the new campaign exactly once on the dashboard.
- [ ] All unit tests pass and all source files remain <500 lines.
