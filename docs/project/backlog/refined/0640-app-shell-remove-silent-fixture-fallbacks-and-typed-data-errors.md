---
id: '0640'
title: App Shell Removes Silent Fixture Fallbacks and Reports Typed Data Errors
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0066
- US-0068
target_release: 0.9.0
severity: high
source_audits:
- w2-app-shell.md
---

# TASK-0640: App Shell Removes Silent Fixture Fallbacks and Reports Typed Data Errors

## Status
Refined

## Summary
`frontend/src/services/app-data-service.ts` replaces every failed backend read with canned fixture data, and it reports failed writes as successes. Change the data layer so that a failed call returns a typed error. Views show an explicit error or empty state. Fixture modules are imported only by Storybook stories and unit tests. A failed mutation tells the user that nothing was saved.

## Problem Statement
- `frontend/src/services/app-data-service.ts:40-48` `request()` returns `null` on any non-OK response or exception. The callers then substitute fixtures:
  - `fetchCampaigns` (line 61-63) uses `FALLBACK_CAMPAIGNS`.
  - `fetchCampaign` (line 72) uses `FALLBACK_CAMPAIGNS` or `createFallbackCampaign`.
  - `fetchCampaignMembers`, `fetchCampaignSessions` (`getFallbackCampaignSessions`), `fetchCharacters` (line 106), `fetchBoardState` (line 166), and `fetchLobbyState` (line 159) substitute fixture arrays.
- Writes succeed locally when the backend fails. `createCharacter` (line 142), `createCampaign` (lines 183-184, which mutates the global `FALLBACK_CAMPAIGNS`), `createCampaignSession` (lines 175-177), `assignMemberRole` (line 79), `removeCampaignMember` (line 89), and `deleteCharacter` (line 150) all update local state after a failure.
- Result: the App Shell shows invented data as live data, and a failed save looks successful.

## Documentation & Architecture Review
- `AGENTS.md` DoR 9 forbids fallbacks that keep old behaviour alive. Fixture data is a defect to remove, not a shim to keep.
- `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md` and `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md` describe view routing. Update them only where they state fallback behaviour.
- ADR-0004 (Lit and Storybook) allows fixtures in stories. Stories keep their own fixtures.
- ADR-0007: the data layer is a client adapter. It must not invent domain state.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0066-client-side-routing-navigation-and-breadcrumbs.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)
- [`us-0068-app-shell-view-audit-and-api-proxying.md`](../../user_stories/accepted/us-0068-app-shell-view-audit-and-api-proxying.md)

## Detailed Specification & Implementation Plan
1. Replace `request<T>()` with a result type `{ ok: true, data: T } | { ok: false, status: number, message: string }`. Remove the `|| FALLBACK_*` expressions from every public `fetch*` and `create*` method.
2. Mutations return the same result type. A failed mutation does not touch local arrays.
3. Remove the in-place mutation of `FALLBACK_CAMPAIGNS`, `FALLBACK_CHARACTERS`, and `FALLBACK_CAMPAIGN_SESSIONS_MAP` from production code.
4. Move the fixture modules (`app-data-service.fixtures.ts`, `fallback-data.ts`) under `frontend/src/fixtures/` and make them importable only from `*.stories.ts` and `frontend/test/**`. Add a test that greps production sources for those imports.
5. Views (`runefoble-app.ts` and its child components) render an error state with a retry control when a read fails, and an empty state when a read succeeds with no rows. A failed write shows a toast with the server message.
6. Do not add a new fallback. Keep the per-view error component small (one file under `frontend/src/components/state/`).

## Frontdoor Blackbox Test Plan
Playwright BDD scenarios in `e2e/features/app_shell_data_errors.feature` (new file, shared with TASK-0650 conventions):
- Scenario: Opening a campaign that does not exist shows "not found", not a fixture campaign.
  - Given a signed-in player
  - When the player opens `#/campaigns/00000000-0000-0000-0000-000000000000`
  - Then the page shows a not-found state and does not show "Tomb of the Star-Eater".
- Scenario: Creating a campaign with an empty title is rejected and not listed.
  - When the DM submits the create form with an empty title
  - Then a toast shows the server validation message
  - And the campaign list does not contain a new row.
- Scenario: Gateway unavailable shows an error state with retry.
  - Given the gateway is stopped by the test harness (public `make` target, not a route stub)
  - Then the dashboard shows the error state, not canned campaigns.
- Before the fix these scenarios FAIL because fixture campaigns appear. After the fix they PASS.
- Unit tests in `frontend/test/app-data-service.test.ts` cover the result type for each `fetch*` and `create*` method. No network stubs are used for the BDD scenarios.

## Definition of Done
1. No production module under `frontend/src` imports `FALLBACK_*` or `fallback-data`. Verified by a test.
2. Every public method of `app-data-service.ts` returns the typed result. No `|| FALLBACK` remains.
3. The three Playwright BDD scenarios pass in chromium, firefox, and webkit with no backdoor state.
4. `pnpm run lint`, `pnpm test`, and `pnpm run build` pass in `frontend/`.
5. Storybook stories still build with their own fixtures and show zero console errors.
6. Every changed file is under 500 lines.
7. `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md` no longer describes fallback data.
