---
id: '0535'
title: Frontdoor Negative Authentication Suite (Forged, Expired, Wrong Audience, Body Claims)
status: Refined
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0521
- TASK-0523
- TASK-0534
governing_adrs:
- ADR-0014
- ADR-0007
governing_prds:
- PRD-0023
governing_stories:
- US-0062
- US-0013
target_release: 0.9.0
severity: high
source_audits:
- w1-libs.md
- w3-authz-coverage.md
- w2-e2e-bdd.md
---

# TASK-0535: Frontdoor Negative Authentication Suite (Forged, Expired, Wrong Audience, Body Claims)

## Status
Refined

## Summary
The existing 209 authentication tests pass only because dev mode accepts anything. No test sends a forged or invalid token through a public route and expects a refusal. Add a parameterised frontdoor suite that covers every class of bad credential on representative routes in each surface. Run it in the normal test gate.

## Problem Statement
- Audit w3-authz: the 209 auth and WebSocket tests pass under the mock and dev mode. None checks a refused token.
- Audit w1-libs F15: no unit tests cover JWT verification, audience, issuer, or claim sync.
- Audit w2-e2e-bdd F13: the browser suite forges tokens and sets dev mode, so it never checks signature validation.
- The gateway and the services each have their own dependency. Without a suite that targets each one, a service can regress silently.

## Documentation & Architecture Review
- Invariant 7 (frontdoor only): the suite uses HTTP, WebSocket, and OpenAPI only. No private state.
- ADR-0014 requires BDD scenarios for user flows. This suite covers the negative identity flows as scenarios in a Gherkin feature file as well as in pytest, so the traceability stays with the user stories (US-0062, US-0013).
- Test helpers come from TASK-0520 (`runefoble_auth/testing`). Do not add a second signing helper.

## Product & User Story References
- US-0062 (sign-in must refuse invalid credentials). US-0013 (every gateway call uses a verified subject).

## Detailed Specification & Implementation Plan
1. New pytest module `tests/test_blackbox_identity_negative.py`, parameterised over:
   - Credential: none; garbage string; HS256 with a known secret; `alg: none`; unsigned; RS256 from an unknown key; expired; wrong `aud`; wrong `iss`; missing `sub`; valid token but for a different audience used on a service route.
   - Surface: gateway profile (`GET /api/v1/profile`), gateway campaign create (`POST /api/v1/campaigns`), gateway asset upload, one service route per migrated service (board_state, campaign_lore, rules_compendium, voice_agent), gateway WebSocket session connect.
   - Expectation: 401 on HTTP, handshake denied on WebSocket.
2. Retired routes: `POST /api/v1/auth/token`, `POST /api/v1/auth/admin/seed`, and `POST /api/v1/auth/sync/user` return 404 or 405.
3. Dev flag is dead: set `RUNEFOBLE_AUTH_DEV_MODE=true` and `AUTH_DEV_MODE=true` in the environment for the whole module. Every negative case still returns 401.
4. Gherkin mirror: add `e2e/features/identity-negative.feature` with the three most important cases (forged token on profile, retired sign-in endpoint, body-claim sync). Each scenario is executed by the Playwright BDD runner through the App Shell or the public API.
5. Wire the module into the default pytest gate (`uv run pytest`). Do not mark it slow.

## Frontdoor Blackbox Test Plan
The suite is the test plan. Each case is one public request and one observable refusal.
- Before: most cases return 200 or accept the connection.
- After: every case refuses the credential. The Gherkin mirror passes in the browser runner.

## Definition of Done
1. `uv run pytest tests/test_blackbox_identity_negative.py` passes. Count the cases in the output and include the count in the PR.
2. The Gherkin feature file runs and passes in `make test-e2e`.
3. No test in the repo sets `RUNEFOBLE_AUTH_DEV_MODE=true` to obtain a pass, except this module's negative guard in step 3.
4. The authentication test count in `docs/reference` (if stated) is updated.
5. No file exceeds 500 lines.
