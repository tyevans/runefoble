---
id: '0475'
title: Gateway Campaign Invite Preview API and Client-Side Invite Acceptance Route
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0208
- TASK-0210
- TASK-0353
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0005
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0066
target_release: 0.9.0
---

# TASK-0475: Gateway Campaign Invite Preview API and Client-Side Invite Acceptance Route

## Status
Proposed

## Summary
Add a public preview endpoint (`GET /api/v1/campaigns/invites/{token}`) to the Gateway API, register the client SPA route `#/join/:inviteToken` in `frontend/src/router/router.ts`, implement `<runefoble-campaign-join-card>` Lit Web Component in `services/game_session/ui/src/campaigns/`, and wire invite preview and acceptance orchestration into `frontend/src/runefoble-app.ts` and `AppDataService`.

## Problem Statement
When a Game Master generates a shareable invite link (`https://.../#/join/:token`) via `<runefoble-campaign-members>` (`TASK-0210`, `TASK-0353`), there is no public endpoint in `gateway/api/src/gateway_api/routers/campaigns.py` to inspect the invite details (campaign title, description, setting, DM display name, pre-assigned role, expiration status) without prematurely consuming the invite token. Furthermore, `frontend/src/router/router.ts` does not include `#/join/:inviteToken` in `STANDARD_ROUTES`, causing invited players who open an invite link to be dumped on the fallback view without context. There is also no dedicated acceptance card or modal allowing the player to review the party details, authenticate if necessary, and accept the invite in one click.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Adding invited users to campaign membership via SpiceDB Zanzibar `player` or `spectator` relation upon invite acceptance.
- **ADR-0004: Lit Web Components and Storybook UI**: Designing `<runefoble-campaign-join-card>` with high-contrast Bauhaus design tokens and Shadow DOM encapsulation.
- **ADR-0005: Zitadel OIDC Authentication**: Verifying authenticated user token before granting campaign access, prompting unauthenticated visitors with the login modal.
- **ADR-0013: Frontend Microfrontend Architecture**: Vendoring the invite acceptance component inside the `game_session` bounded context (`services/game_session/ui/src/campaigns/`) and aggregating into Storybook.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
- [`us-0066-client-side-routing-navigation-and-breadcrumbs.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)

## Scope of Work
1. **Gateway API Invite Preview Endpoint (`gateway/api/src/gateway_api/routers/campaigns.py`)**:
   - Implement `GET /api/v1/campaigns/invites/{token}`:
     - Look up token in `InviteManager` / `campaign_store`.
     - Validate expiration timestamp and max uses without incrementing use count.
     - Look up campaign metadata (title, description, system, cover image) and DM host display name.
     - Return `CampaignInvitePreviewResponse` containing `token`, `campaign_id`, `campaign_title`, `description`, `system`, `role`, `dm_name`, `expires_at`, and `is_valid`.
2. **Client Router Registration (`frontend/src/router/router.ts`)**:
   - Add `#/join/:inviteToken` to `STANDARD_ROUTES`.
   - Update breadcrumb resolver to display `Home > Join Campaign`.
3. **Invite Acceptance Web Component (`services/game_session/ui/src/campaigns/runefoble-campaign-join-card.ts`)**:
   - Create Bauhaus-styled card displaying campaign title, DM host badge, role pre-assignment badge, and ruleset.
   - Show expiration warnings or "Invite Expired" disabled state when invalid.
   - Dispatch `@accept-invite` custom event with `{ token: string, campaignId: string }`.
   - Add Storybook stories in `services/game_session/ui/src/campaigns/runefoble-campaign-join-card.stories.ts`.
4. **App Data Service & App Shell Orchestration (`frontend/src/runefoble-app.ts` & `frontend/src/services/app-data-service.ts`)**:
   - Add `previewCampaignInvite(token: string)` and `acceptCampaignInvite(token: string)` with standalone/offline fixture fallbacks.
   - In `runefoble-app.ts`, handle view `'campaign-join'`, preview invite details, check authentication status, prompt `<runefoble-auth-modal>` if guest, and on acceptance execute `POST /api/v1/campaigns/join` and route to `#/campaigns/:campaignId`.

## Definition of Done
1. `GET /api/v1/campaigns/invites/{token}` returns invite metadata and usability status without consuming uses.
2. `#/join/:inviteToken` is a deep-linkable client route recognized by `Router`.
3. `<runefoble-campaign-join-card>` renders in Storybook with 100% Bauhaus design tokens in dark and light modes.
4. Invited users can accept an invite and immediately transition to the campaign dashboard with Zanzibar relations updated.
5. All source files conform strictly to Hard Invariant 6 (< 500 lines).
