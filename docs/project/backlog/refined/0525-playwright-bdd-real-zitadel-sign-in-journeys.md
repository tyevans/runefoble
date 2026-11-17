---
id: '0525'
title: Playwright BDD Journeys Authenticate Through Real Zitadel
status: Refined
created: 2026-11-17
dependencies:
- TASK-0524
- TASK-0526
- TASK-0538
governing_adrs:
- ADR-0014
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0062
target_release: 0.9.0
severity: high
source_audits:
- w2-e2e-bdd.md
- w2-app-shell.md
---

# TASK-0525: Playwright BDD Journeys Authenticate Through Real Zitadel

## Status
Refined

## Summary
The end-to-end suite signs users in with tokens that the test code forges. The Playwright web server runs with dev mode on. Replace this with real sign-in through the Zitadel OIDC flow. Test users are created through the Zitadel management API, which is a public frontdoor.

## Problem Statement
- `e2e/support/auth_fixtures.ts:82-130` builds a JWT with a fixed mock signature. Lines 187-205 (`injectUserIntoPage`) write those tokens into local storage. Line 123 uses the literal `mock-zitadel-signature-for-frontdoor-bdd`. Audit w2-e2e-bdd F13.
- `playwright.config.ts:83-88` sets `AUTH_DEV_MODE=true` for the web server. TASK-0520 removes that variable.
- `e2e/features/smoke.feature:6-9` checks only that a guest reaches `#/login`. No scenario signs in through the form or the OIDC flow.
- ADR-0014 allows local-storage token injection. It does not allow forged tokens. Injected tokens must come from Zitadel.

## Documentation & Architecture Review
- ADR-0014 (BDD and Playwright) and `docs/how-to/validate-e2e-journeys-with-playwright-bdd.md` and `docs/how-to/test-user-flows-with-playwright-bdd.md`. Update both where they describe token fixtures.
- Test users are provisioned through the Zitadel management API, not the database (invariant 7).
- The Zitadel application and bootstrap service account come from TASK-0526.

## Product & User Story References
- US-0062 scenarios (sign-up, sign-in, and profile) must run in the suite. The fixture that writes local storage is audit w2-app-shell F11.
- PRD-0023 acceptance (guard and redirect).

## Detailed Specification & Implementation Plan
1. **Global setup**: create the test personas (`dm`, `player`) through the Zitadel management API, using the bootstrap service account from TASK-0526. Do not write to any database.
2. **Sign-in fixture**: `signInAs(persona)` runs the real OIDC flow in the browser against Zitadel. Save the storage state per persona under `e2e/.auth/` (git-ignored).
3. **Delete** the mock JWT builders and the `injectUserIntoPage` forging path. A helper may inject a token only if that token came from Zitadel in the same run.
4. **Web server**: remove `AUTH_DEV_MODE` from `playwright.config.ts`. Run the stack with the Helm or Kind values from TASK-0526.
5. **Feature files**: add real sign-in and sign-out scenarios to `smoke.feature`. Implement US-0062 scenarios 1 and 2 with real steps.
6. **Negative scenario**: a request with a forged token gets 401 from the gateway (`Given a token signed by an unknown key`, `When I open my profile`, `Then the App Shell shows the signed-out state`).
7. **Make target**: `make test-e2e` runs global setup. No extra manual steps.

## Frontdoor Blackbox Test Plan
Browser journeys through the App Shell only.
- Before: the suite passes with forged tokens. Dev mode is on.
- After:
  - Sign-in as `dm` through the Zitadel page reaches `#/campaigns`.
  - Wrong password shows Zitadel's error. No App Shell session exists.
  - The forged-token scenario shows the signed-out state.
  - No test reads or writes a database.
  - The suite passes in multi-browser runs (existing configuration).

## Definition of Done
1. `grep -rn "mock-zitadel-signature\|AUTH_DEV_MODE\|injectUserIntoPage" e2e playwright.config.ts` returns no matches.
2. `make test-e2e` passes against the Kind stack with a real Zitadel.
3. The two how-to guides describe the Zitadel fixture.
4. Storybook and frontend builds still pass (no change expected).
5. No file exceeds 500 lines. New step files are split by feature.
