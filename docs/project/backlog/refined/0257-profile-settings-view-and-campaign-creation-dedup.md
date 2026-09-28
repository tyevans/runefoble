---
id: '0257'
title: Profile Settings View and Campaign Creation Idempotency
status: Refined
created: 2026-09-27
dependencies:
- TASK-0206
- TASK-0209
- TASK-0213
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0007
- ADR-0012
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
Refined

## Summary
Implement the user profile view (`#/profile`) in `frontend/src/runefoble-app.ts` to resolve the no-op when clicking "Account Settings" in the user menu. Fix the campaign creation defect where a newly created campaign appears twice in the dashboard list by stopping duplicate event propagation in `RunefobleCampaignDashboard` / `RunefobleCampaignCreator` and enforcing ID de-duplication in `AppDataService`.

## Problem Statement
Two critical frontend navigation and data flow defects currently degrade user experience:
1. **Account Settings No-Op**: Clicking "Account Settings" in `runefoble-user-menu` routes to `#/profile`, but `getActiveView()` has no pattern for `#/profile` and falls through to `'campaigns'`. The user remains stuck on the dashboard.
2. **Duplicate Campaign Listing**: When a campaign is submitted via `<runefoble-campaign-creator>`, the modal dispatches a bubbling composed `create-campaign` event. The parent `<runefoble-campaign-dashboard>` captures this and dispatches a second `create-campaign` event without stopping propagation. The shell handles both events and triggers two creation calls, rendering duplicate campaign cards.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/authenticate-with-zitadel-oidc.md`: Profile claims and user info endpoints.
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: SPA route registration, parameter extraction, and view rendering.
  - `docs/reference/ports-and-endpoints.md`: `GET /api/v1/profile` endpoint definition.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit component isolation and event dispatch patterns.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: User identity verification and role claims.
  - **ADR-0004: Lit Web Components and Storybook UI**: Microfrontend encapsulation and Bauhaus design tokens.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain separation between gateway auth and app shell.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast card styling for profile claims.
  - **ADR-0013: Frontend Microfrontend Architecture**: Event bubbling containment and view isolation.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Stories**:
  - [`us-0062-user-registration-zitadel-auth-and-profile.md`](../../user_stories/accepted/us-0062-user-registration-zitadel-auth-and-profile.md)
  - [`us-0070-user-account-settings-and-profile-management.md`](../../user_stories/accepted/us-0070-user-account-settings-and-profile-management.md)
  - [`us-0071-campaign-dashboard-idempotency-and-lifecycle.md`](../../user_stories/accepted/us-0071-campaign-dashboard-idempotency-and-lifecycle.md)

## Detailed Specification & Implementation Plan
1. **Profile View Component (`frontend/src/components/runefoble-user-profile.ts`)**:
   - Create Lit Web Component rendering user profile claims (`user_id`, `username`, `email`, `roles`, `is_admin`) retrieved from `GET /api/v1/profile` or `authService.getUser()`.
   - Include role badges, current theme / color mode display, and session logout trigger.
2. **App Shell Profile Route (`frontend/src/runefoble-app.ts`)**:
   - Add `'profile'` to `AppActiveView` union type.
   - In `getActiveView()`, return `'profile'` when `pat === '#/profile'`.
   - In `renderActiveView()`, mount `<runefoble-user-profile>`.
   - Update breadcrumb trail to `[{ label: 'Home', path: '#/campaigns' }, { label: 'Account Settings', path: '#/profile' }]`.
3. **Event Propagation & Idempotency Fix**:
   - In `services/game_session/ui/src/campaigns/runefoble-campaign-dashboard.ts`:
     - In `handleCreatorSubmit(e: CustomEvent)`, call `e.stopPropagation()` to prevent double dispatch to the parent App Shell.
   - In `frontend/src/services/app-data-service.ts`:
     - In `fetchCampaigns()` and `createCampaign()`, ensure `FALLBACK_CAMPAIGNS` de-duplicates entries by `id` using a `Map<string, CampaignItem>`.
4. **Blackbox Frontdoor Verification (`tests/test_blackbox_profile_and_campaign_creation.py`)**:
   - Verify navigation to `#/profile` mounts the profile component and displays claims.
   - Verify submitting campaign creation creates exactly one campaign item and triggers a single API/state update.

## INVEST Criteria Evaluation
- **Independent (I)**: Addresses profile view rendering and event bubbling without cross-service blockers.
- **Negotiable (N)**: Profile avatar rendering and supplementary claim fields can be extended.
- **Valuable (V)**: Fixes a broken menu navigation link and eliminates duplicate campaign creation bugs.
- **Estimable (E)**: Pure frontend Lit component creation and event isolation sized for a single pass.
- **Small (S)**: Kept under 140 lines of changes across component and shell files.
- **Testable (T)**: Frontdoor route assertions and event dispatch spy tests verify fix.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Clicking "Account Settings" in the user menu navigates to `#/profile` and mounts `<runefoble-user-profile>`.
2. User profile displays username, email address, role badges, and theme selection.
3. Submitting the campaign creation modal dispatches exactly one event, appending exactly one campaign to the dashboard.
4. `AppDataService` enforces campaign ID uniqueness.
5. Blackbox frontdoor tests pass via `uv run pytest tests/test_blackbox_profile_and_campaign_creation.py`.
6. All modified files strictly adhere to file length limit (<500 lines).
