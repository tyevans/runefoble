---
id: '0654'
title: Gherkin and Playwright Coverage for Register, Login, Create Campaign, and Invite Join
status: Refined
created: 2026-11-17
dependencies:
- TASK-0652
- TASK-0524
- TASK-0525
governing_adrs:
- ADR-0014
- ADR-0001
governing_prds:
- PRD-0023
governing_stories:
- US-0062
- US-0063
target_release: 0.9.0
severity: high
source_audits:
- w2-e2e-bdd.md
---

# TASK-0654: Gherkin and Playwright Coverage for Register, Login, Create Campaign, and Invite Join

## Status
Refined

## Summary
The first half of the core journey plan: a new player registers and signs in, a DM creates a campaign and assigns roles, and a player joins through an invite link. Write the Gherkin scenarios first. Then add the steps, using only public frontdoors. The scenarios cite their user stories by tag (TASK-0656). This task covers journeys 1 to 3 of the six core journeys named in the synthesis brief. Journeys 4 to 7 are in TASK-0655.

## Problem Statement
- Coverage is far below the accepted stories. Only US-0063 (campaign creation and roles) has an end-to-end scenario, and it is partial (`w2-e2e-bdd.md` F12).
- Register and login have no scenario. The smoke scenario only reaches `#/login` (`smoke.feature:6-9`).
- The invite join flow has a clipboard assertion that can pass without a check (`w2-e2e-bdd.md` F8). The invite preview route is in proposed TASK-0475.

## Documentation & Architecture Review
- `docs/how-to/manage-campaign-lifecycle-and-invites.md` describes the invite and join contract. The scenarios follow it.
- `docs/how-to/test-user-flows-with-playwright-bdd.md` defines the scenario layout and step rules.
- ADR-0014 requires Gherkin before steps. Write the feature file first and review it before writing any step.
- Blocked in part: the register and login scenarios need the identity theme's real sign-in (TASK-0524 for the App Shell OIDC flow and TASK-0525 for the Playwright real-Zitadel fixture). Until they land, the scenarios are written with `@blocked-auth` and excluded from the default run. They must not use storage injection. TASK-0525 owns the sign-in fixture; this task only uses it.

## Product & User Story References
- [`us-0062-user-registration-zitadel-auth-and-profile.md`](../../user_stories/accepted/us-0062-user-registration-zitadel-auth-and-profile.md)
- [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)

## Detailed Specification & Implementation Plan
1. Write `e2e/features/core_identity_and_campaign.feature` with these scenarios (tagged with the story id, see TASK-0656):
   - `@US-0062` A new player registers, verifies the email code from Mailpit, and reaches the dashboard.
   - `@US-0062` A registered player signs in with the correct password and sees their profile name.
   - `@US-0063` A DM creates a campaign from the dashboard and sees it listed with the DM role.
   - `@US-0063` The DM assigns a player the "player" role and the player sees the campaign on their dashboard.
   - `@US-0063` The DM creates an invite; a second player opens the link, accepts, and sees the campaign.
   - `@US-0063` A player who has not been invited sees "not found or no access" for the campaign URL.
2. Write the steps in `e2e/steps/identity_steps.ts` and `e2e/steps/invite_steps.ts`. Setup uses `frontdoor_api.ts` and the public UI only. Do not inject roles into component state.
3. Mailpit: read the verification code from the Mailpit HTTP API (`/mail` ingress), not from the database.
4. Clipboard: the invite copy step asserts the clipboard value equals the invite URL (grant `clipboard-read`).
5. Keep each step file under 500 lines.

## Frontdoor Blackbox Test Plan
The six scenarios above are the test plan. Each one runs in chromium, firefox, and webkit. Before the work, none of them exists, so every scenario is red. After the work, all pass. The uninvited-player scenario also asserts the gateway returns 403 or 404 for `GET /api/v1/campaigns/{id}` (Playwright API request in the same scenario, public route only).

## Definition of Done
1. `e2e/features/core_identity_and_campaign.feature` exists with the six scenarios, each tagged with its story id.
2. The scenarios pass in all three browsers. The two auth-dependent scenarios pass once TASK-0524 and TASK-0525 have landed, and their tag is removed at that time.
3. No step injects state, writes `localStorage`, or dispatches synthetic events (grep check from TASK-0649).
4. `make test-bdd` passes (Gherkin and step coverage).
5. Each file is under 500 lines.
