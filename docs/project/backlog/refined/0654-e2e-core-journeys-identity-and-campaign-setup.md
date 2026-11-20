---
id: '0654'
title: Gherkin and Playwright Coverage for Register, Login, Create Campaign, and Invite Join
status: Refined
created: 2026-11-17
dependencies:
- TASK-0652
- TASK-0950
governing_adrs:
- ADR-0014
- ADR-0001
governing_prds:
- PRD-0023
- prd-0025-voice-first-release-one
governing_stories:
- US-0062
- US-0063
target_release: 1.0.0
---

# TASK-0654: Gherkin and Playwright Coverage for Register, Login, Create Campaign, and Invite Join

## Status
Refined. Updated 2026-11-19 for Release One (PRD-0025). Evidence from `.audit/research/r1-core-journeys.md`, section 3.

## Summary
The first half of the core journey plan: a new player registers and signs in, a DM creates a campaign and assigns roles, and a player joins through an invite link. Write the Gherkin scenarios first. Then add the steps, using only public frontdoors. The scenarios cite their user stories by tag (TASK-0656). This task covers journeys 1 to 3 of the six core journeys named in the synthesis brief. Journeys 4 to 7 are in TASK-0655.

Login is already covered by `smoke.feature`. This task adds the register path, the profile check, the campaign role path, the invite join through the UI, and the uninvited-player check.

## Problem Statement
- Coverage is far below the accepted stories. Only US-0063 (campaign creation and roles) has an end-to-end scenario, and it is partial (`w2-e2e-bdd.md` F12).
- Login is covered. `e2e/features/smoke.feature:12-17` signs in through Zitadel and reaches `#/campaigns`. `:19-23` covers a wrong password, and `:26-30` covers sign-out. The profile name is not checked.
- Register has no scenario. No Mailpit helper exists under `e2e/`.
- The invite join has no App Shell route (`frontend/src/router/router.ts:28-33`). TASK-0950 adds it. Until then, the join step cannot use the UI.
- The clipboard check accepts a link that contains `sample_token`. `e2e/steps/campaign_hub_steps.ts:245` and `:260` match any `/join/` value. The clipboard equality check at `:262-263` is correct.
- The uninvited-player text "not found or no access" does not exist in the UI. The only not-found component is `frontend/src/components/state/runefoble-data-error.ts`.

## Documentation & Architecture Review
- `docs/how-to/manage-campaign-lifecycle-and-invites.md` describes the invite and join contract. The scenarios follow it.
- `docs/how-to/test-user-flows-with-playwright-bdd.md` defines the scenario layout and step rules.
- ADR-0014 requires Gherkin before steps. Write the feature file first and review it before writing any step.
- Sign-in fixture: `e2e/support/auth_fixtures.ts:1-9` states that every persona uses real Zitadel sign-in. TASK-0524 and TASK-0525 are complete, so no `@blocked-auth` tag exists. The scenarios must not use storage injection. A restored session is a real Zitadel session from the first sign-in in the worker.

## Product & User Story References
- [`us-0062-user-registration-zitadel-auth-and-profile.md`](../../user_stories/accepted/us-0062-user-registration-zitadel-auth-and-profile.md)
- [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
- PRD-0025, "What good looks like", step 1.

## Detailed Specification & Implementation Plan
1. Write `e2e/features/core_identity_and_campaign.feature` with these scenarios (tagged with the story id, see TASK-0656):
   - `@US-0062` A new player registers, verifies the email code from Mailpit, and reaches the dashboard. This scenario is new.
   - `@US-0062` A registered player signs in with the correct password and sees their profile name. The sign-in part is covered by `smoke.feature:12-17`. This scenario adds the profile name check.
   - `@US-0063` A DM creates a campaign from the dashboard and sees it listed with the DM role.
   - `@US-0063` The DM assigns a player the "player" role. The player then sees the campaign on their dashboard. The role change is covered by `campaign_hub.feature:12-16`. The player dashboard check is new.
   - `@US-0063` The DM creates an invite. A second player opens the link in the App Shell, signs in if needed, joins, and sees the campaign. This depends on TASK-0950.
   - `@US-0063` A player who has not been invited is refused. The step asserts the state that `runefoble-data-error` shows for a 404 and the API status (403 or 404) for `GET /api/v1/campaigns/{id}`.
2. Write the steps in `e2e/steps/identity_steps.ts` and `e2e/steps/invite_steps.ts`. Setup uses `frontdoor_api.ts` and the public UI only. Do not inject roles into component state.
3. Mailpit: read the verification code from the Mailpit HTTP API (`/mail` ingress), not from the database. Before writing the register scenario, confirm that the test Zitadel stack allows sign-up (`.audit/research/r1-core-journeys.md`, section 5).
4. Clipboard: the invite copy step asserts that the clipboard value equals the invite URL, and that the URL is absolute and contains a token. It must reject `sample_token`. Grant `clipboard-read`.
5. Keep each step file under 500 lines.

## Frontdoor Blackbox Test Plan
The six scenarios above are the test plan. Each one runs in chromium, firefox, and webkit. Before the work, the register, profile, invite and uninvited scenarios do not exist, so they are red. After the work, all pass. The uninvited-player scenario also asserts the gateway status for `GET /api/v1/campaigns/{id}` (Playwright API request in the same scenario, public route only).

## Definition of Done
1. `e2e/features/core_identity_and_campaign.feature` exists with the six scenarios, each tagged with its story id.
2. The scenarios pass in all three browsers. The invite scenario depends on TASK-0950 and runs after it lands.
3. No step injects state, writes `localStorage`, or dispatches synthetic events (grep check from TASK-0649).
4. `make test-bdd` passes (Gherkin and step coverage).
5. `git grep -n "sample_token" e2e` returns no match in the invite steps.
6. Each file is under 500 lines.

## Orchestrator Addenda (2026-11-17)

Source: `.audit/synth/discovered-round1.md`.

- Empty title: `services/game_session/ui/src/campaigns/runefoble-campaign-creator.ts` marks the title input `required`, so an empty submit never reaches the server. Decide the spec: client validation message or server 422.

## Audit Provenance

- Severity: high
- Source audits: `w2-e2e-bdd.md`; `.audit/research/r1-core-journeys.md` (section 3, 0654 table)
