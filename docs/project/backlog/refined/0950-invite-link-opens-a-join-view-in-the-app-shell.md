---
id: '0950'
title: An Invite Link Opens a Join View in the App Shell
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds:
- prd-0025-voice-first-release-one
governing_stories:
- us-0062-user-registration-zitadel-auth-and-profile
- us-0063-campaign-creation-dashboard-and-zanzibar-roles
target_bc: game_session
target_release: 1.0.0
---

# TASK-0950: An Invite Link Opens a Join View in the App Shell

## Status

Refined. Release One (PRD-0025). Journey step 1 of `.audit/research/r1-core-journeys.md`.

## Summary

A friend cannot join a campaign in the App Shell. The DM copies an invite link of the form `/#/join/<token>`. The App Shell has no route for that path, so it shows the campaigns dashboard. A signed-out visitor goes to sign-in, and the token is lost when sign-in ends. The DM invite field also shows a fake token (`sample_token`) before a link exists.

This task adds the join route, keeps the token through sign-in, and joins the campaign through the gateway route. It also removes the fake token and returns a full invite URL.

## Problem Statement

Evidence from `.audit/research/r1-core-journeys.md`, section 4, items 1 and 3.

- `frontend/src/router/router.ts:28-33`: `STANDARD_ROUTES` has no `#/join/:token` pattern.
- `frontend/src/router/view-resolver.ts:48`: an unknown pattern resolves to `'campaigns'`.
- `frontend/src/router/auth-guard.ts:24`: a signed-out visitor is sent to `#/login`.
- `frontend/src/app/auth-callback.ts:11`: after sign-in the App Shell opens `#/campaigns`. The join path is not kept.
- `frontend/src/services/app-data-service.ts:171-173`: the only seat method is `joinSession` (lobby seat). No campaign join method exists.
- `gateway/api/src/gateway_api/routers/campaigns_proxy.py:89-91`: the gateway proxies `POST /api/v1/campaigns/join`. No UI calls it.
- `services/game_session/src/game_session/campaign/service_membership.py:67`: the server returns a relative `invite_url` (`/#/join/{token}`). A clipboard value built from it is a path, not a link.
- `services/game_session/ui/src/campaigns/runefoble-campaign-members.ts:51-53`: `effectiveInviteUrl` returns `sample_token` when no token exists.
- `frontend/src/app/campaign-actions.ts:83`: the real token is set only after the DM clicks "Generate Link".
- `e2e/steps/campaign_hub_steps.ts:245` and `:260`: the link checks accept any `/join/` value, so `sample_token` passes.

## Documentation & Architecture Review

- `docs/how-to/manage-campaign-lifecycle-and-invites.md` documents the invite contract and the `/#/join/{token}` URL. Update its join section when this task lands.
- `docs/reference/microfrontend-architecture.md` lists the component catalog. Add `<runefoble-campaign-join>`.
- `docs/how-to/authoring-service-microfrontends.md`: the join view is a Lit element in the owning service (`services/game_session/ui/`). The App Shell mounts it (ADR-0013).
- `docs/reference/ui-transport.md`: the join call uses the shared browser client.
- ADR-0015: no substitute token and no substitute URL.
- ADR-0001: membership is checked by the owner. The client does not decide access.
- `TASK-0475` (proposed) covers a gateway invite preview route. This task does not need that route. If TASK-0475 stays in the backlog, its scope must not repeat the App Shell join route.

## Product & User Story References

- PRD-0025, "What good looks like", step 1, and Checkable Outcome 1.
- US-0063: campaign membership and invites.
- US-0062: sign-up and sign-in.

## Detailed Specification & Implementation Plan

1. **Route.** Add `#/join/:token` to `STANDARD_ROUTES` in `frontend/src/router/router.ts`. Map it to a new view id `campaign-join` in `frontend/src/router/view-resolver.ts`, and add the id to `AppActiveView`.
2. **Sign-in keeps the join path.** When the auth guard (`frontend/src/router/auth-guard.ts:24`) sends a visitor to sign-in for a join path, it stores the hash path in `sessionStorage` under one key. The key holds a route path only. It holds no credential. After `completeSignInCallback` (`frontend/src/app/auth-callback.ts:11`) succeeds, the App Shell opens the stored path and removes the key. A missing key keeps the current default (`#/campaigns`).
3. **Join element.** Add `<runefoble-campaign-join>` in `services/game_session/ui/src/campaigns/runefoble-campaign-join.ts`. It takes the token as a property. It shows three states: joining, joined (campaign name and an "Open campaign" link), and refused (the server message). It has no fallback text for a missing token. The App Shell calls a new data service method `joinCampaign(inviteToken)` in `frontend/src/services/app-data-service.ts`. The method posts `{ invite_token }` to `POST /api/v1/campaigns/join`. The reply has `campaign_id` and `role` (`services/game_session/src/game_session/campaign/schemas.py:81-87`). On success the App Shell opens `#/campaigns/<campaign_id>`.
4. **Invite field.** In `services/game_session/ui/src/campaigns/runefoble-campaign-members.ts`, remove the `sample_token` fallback. Show the link field only after the DM generates a token in the current view. The App Shell builds the full URL with `new URL(inv.data.invite_url, window.location.origin)` in `frontend/src/app/campaign-actions.ts`, before it sets `inviteUrl`. The copy action copies that full URL.
5. **E2E setup.** Replace the API redemption with a UI join. Remove the call to `frontdoorApi.joinCampaign` in `e2e/steps/vtt_setup_steps.ts:58` and `e2e/steps/session_lobby_roles_steps.ts:79`. The steps open the copied link in a second browser context and join through the UI.
6. **Storybook.** Add `runefoble-campaign-join.stories.ts` with the joining, joined and refused states. The stories must show zero console errors.
7. **Docs.** Update the invite how-to, the component catalog, and `docs/reference/ports-and-endpoints.md` when the App Shell join route is in use.

## Frontdoor Blackbox Test Plan

Playwright BDD scenarios in a new feature file `e2e/features/campaign_invite_join.feature`. Setup uses only the UI. Each scenario runs in chromium, firefox and webkit.

```gherkin
@US-0063 @US-0062
Feature: An invite link joins a campaign in the App Shell

  Scenario: The invite field stays hidden until the DM generates a link
    Given Evelyn creates campaign "Invite Campaign" in the UI
    When Evelyn opens "Invite Adventurers" for the campaign
    Then no shareable link field is shown

  Scenario: A friend opens the invite link, signs in, and joins the campaign
    Given Evelyn creates campaign "Invite Campaign" in the UI
    And Evelyn generates a player invite link in the UI and copies it
    When Sarah opens the copied invite link in a new browser context
    And Sarah completes the Zitadel sign-in
    Then Sarah sees the campaign "Invite Campaign" with the role "Player"
    And the campaign list of Sarah shows "Invite Campaign"

  Scenario: The copied link is a full URL with a real token
    Given Evelyn creates campaign "Invite Campaign" in the UI
    And Evelyn generates a player invite link in the UI
    Then the copied link starts with the App Shell origin and contains "#/join/"
    And the copied link does not contain "sample_token"

  Scenario: A refused invite shows the server message
    Given Sarah is signed in
    When Sarah opens the link "#/join/not-a-real-token"
    Then Sarah sees the refusal from the server
    And Sarah is not added to any campaign
```

The existing UI steps in `e2e/steps/campaign_hub_steps.ts` create the campaign and open the invite dialog. The clipboard check must compare the copied value with a full URL. It must not accept `sample_token`.

## Definition of Done

1. `#/join/:token` resolves to the `campaign-join` view. A unit test of `resolveActiveView` covers the mapping.
2. The join path survives the Zitadel sign-in. Scenario 2 passes in chromium, firefox and webkit.
3. `git grep -n sample_token -- services frontend e2e` returns no match.
4. The copied invite URL is absolute, contains `#/join/`, and equals the value in the link field.
5. `git grep -n "joinCampaign" e2e/steps` returns no match.
6. `<runefoble-campaign-join>` has a Storybook story. The story shows zero console errors.
7. `docs/how-to/manage-campaign-lifecycle-and-invites.md`, `docs/reference/microfrontend-architecture.md` and `docs/reference/ports-and-endpoints.md` match the code.
8. CHANGELOG `[Unreleased]` records the join route under `Added` and the removed fake token under `Fixed`.
9. No changed source file is over 500 lines.

## Audit Provenance

- Severity: high (blocks journey step 5 of PRD-0025)
- Source audits: `.audit/research/r1-core-journeys.md` (section 1, row 5; section 4, items 1 and 3)
