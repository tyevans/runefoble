---
id: '0967'
title: A Campaign Invite Link Creates the Player Account Through Zitadel
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0023
- ADR-0015
- ADR-0001
governing_prds:
- PRD-0025
governing_stories:
- us-0063-campaign-creation-dashboard-and-zanzibar-roles
target_bc: game_session
target_release: 1.0.0
---

# TASK-0967: A Campaign Invite Link Creates the Player Account Through Zitadel

## Status

Refined

## Summary

ADR-0023 makes release one invite-only: Zitadel self-registration is off, and a valid campaign invite lets a person create an account. The person gives a display name and an email. Runefoble asks Zitadel to create the user with no password. Zitadel sends its own email to verify the address and set the password. The first sign-in completes a pending join to the campaign.

This task is the backend half: the route, the `AccountProvisioner` port and its Zitadel adapter, and the pending join. TASK-0950 builds the join view on top of it.

## Problem Statement

- `services/game_session/src/game_session/campaign/routes.py:118-128`: `POST /join` requires a signed-in caller. A person without an account cannot use an invite.
- `services/game_session/src/game_session/campaign/invite_aggregate.py:24-75`: an invite already has `expires_at`, `max_uses` and `uses`, and `InviteExpiredError` / `InviteExhaustedError` exist (`campaign/errors.py:35-40`).
- `libs/runefoble_auth/src/runefoble_auth/` has `zitadel.py` (token checks) and `zitadel_pat_publisher.py`, but no port that creates a user.
- ADR-0015 (d) and `docs/reference/identity-and-token-contract.md` describe Zitadel hosted sign-up only.

## Documentation & Architecture Review

- ADR-0023 (all decisions), ADR-0015 (a), (b), (d), (e), ADR-0001.
- `docs/reference/identity-and-token-contract.md`, `docs/how-to/authenticate-with-zitadel-oidc.md`, `docs/how-to/manage-campaign-lifecycle-and-invites.md`, `docs/how-to/test-email-signups-with-mailpit.md`, `docs/how-to/add-an-engine-port-adapter.md`, `docs/how-to/test-cross-service-calls-with-live-upstreams.md`.
- Zitadel Management API: create a human user with an email and no password, so that Zitadel sends the initialization email. Read the version of the Zitadel image in `deployments/helm/runefoble/values.yaml` and use the API of that version (context7 or the Zitadel docs).

## Product & User Story References

- PRD-0025, outcome 1 (friends join through the invite link). US-0063.

## Detailed Specification & Implementation Plan

1. **Port.** `libs/runefoble_auth`: `AccountProvisioner` with `async provision(email: str, display_name: str) -> ProvisionedAccount(user_id: str, created: bool)`. Adapter `ZitadelAccountProvisioner` calls the Management API with a service credential read from settings, which Helm fills from a Secret (ADR-0015 (e)). For an email that already has a user, it returns that user with `created=False` and asks Zitadel to send a sign-in or password-reset email. Zitadel unreachable or an error reply: raise an unavailable error. No fallback, no local user.
2. **Route.** `game_session`: `POST /api/v1/campaigns/invites/{token}/accounts`, body `{email, display_name}`, no bearer required. Steps: validate the invite (410 when expired or used up, 404 when unknown), call the provisioner, record one invite use and a `PendingJoinRecorded` event (invite id, Zitadel user id, role) through the invite aggregate (Hard Invariant 2). Answer 202 with the same body for a new and an existing email (ADR-0023 (d)). Zitadel unavailable: 503, no use recorded, no event.
3. **Rate limit.** A limit for each invite and for each client address, with 429 and `Retry-After`. Keep the limiter behind a small port so that a later Redis limiter can replace the in-process one. State the numbers in the reference doc.
4. **Pending join.** `POST /join` (existing) completes the pending join for the caller when the caller's user id matches a pending join of that invite. It writes the SpiceDB `player` relation only at this point (Hard Invariant 1). It does not use a second invite use.
5. **Gateway.** One proxy row for the new route, unauthenticated, in the style of the existing invite rows (ADR-0015 (b)).
6. **Settings and Helm.** Provisioner settings (Zitadel URL, service credential, org id) in Helm from a Secret, with no DEV-ONLY default in the hosted profile (TASK-0955, TASK-0959). Kind uses the existing admin service user.
7. **Docs.** `docs/reference/identity-and-token-contract.md` (new route, rules from ADR-0023 (d)), `docs/how-to/manage-campaign-lifecycle-and-invites.md`, `docs/reference/ports-and-endpoints.md`.

## Frontdoor Blackbox Test Plan

- Pytest through the gateway with a live loopback fake of the Zitadel Management API (a small server in `tests/helpers/`, like `fake_openai_server.py`). No client mocks.
  - Valid invite, new email: 202; the fake received one create-user call with no password; a `PendingJoinRecorded` event is published; `uses` grew by one.
  - Existing email: 202 with the same body; the fake received no create call.
  - Expired invite: 410. Used-up invite: 410. Unknown token: 404. In each case the fake received no call.
  - Fake Zitadel down: 503; no use recorded; no event.
  - Rate limit: the request after the limit gets 429 with `Retry-After`.
  - The new user signs in (signed test token with that user id) and calls `POST /join`: 200, the SpiceDB `player` relation exists, and `uses` did not grow again. Another user with the same token and no pending join follows the normal join rules.
- Orchestrator on Kind (with TASK-0950): a Playwright scenario creates an account from an invite link, reads the Zitadel init email in Mailpit, sets the password on the Zitadel page, signs in, and lands in the campaign.

## Definition of Done

- The tests above pass. The route returns no password, init code or Zitadel detail in any reply or log line.
- Docs updated. CHANGELOG `Added` entry. Each touched file stays under 500 lines.

## Audit Provenance

- Severity: high (release blocker: a friend cannot join without an account).
- Source audits: .audit/research/r1-core-journeys.md (section 4, item 1); user decision 2026-11-19 (ADR-0023).
