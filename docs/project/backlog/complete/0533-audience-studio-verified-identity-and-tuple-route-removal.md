---
id: '0533'
title: Audience Studio Verifies Zitadel Tokens and Removes Body and Header Identity
status: Complete
created: 2026-11-17
dependencies:
- TASK-0526
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0011
governing_stories:
- US-0013
target_release: 0.9.0
---

# TASK-0533: Audience Studio Verifies Zitadel Tokens and Removes Body and Header Identity

## Status
Complete

## Summary
The audience studio service (TypeScript) lets any caller write a DM role tuple and then approve a chaos proposal with it. It takes the acting user from the request body or an `x-user-id` header with a `dm-user` fallback. Verify Zitadel tokens in the service, use the token subject as the actor, and remove the public tuple write route.

## Problem Statement
- `services/audience_studio/src/routes.ts:213-237` (removed) (`POST /auth/tuples`) has no authentication. It writes to the in-memory tuple set. Audit w2-audience-studio F1 (critical).
- Live audit run: `POST /auth/tuples` with `relation: dungeon_master` for `mallory` returned 201, then `POST /proposals/{id}/approve` with `dm_user_id: mallory` returned 200.
- `routes.ts:168-171` and `:195-198` take the acting user from `dm_user_id` in the body or `x-user-id`, with fallback `dm-user`.
- The service has no JWT verification (audit w2-audience-studio F1 and F2).

## Documentation & Architecture Review
- Role hierarchy hardcoded in `src/auth.ts:334-377` and the SpiceDB path that never runs (`auth.ts:380`) are authorization defects (audit w2-audience-studio F2). Out of scope here, except that the removed tuple route is a dependency of that work.
- The tuple write route is a grant path. It is removed here as an identity defect. The authorization theme owns any admin grant path.
- Helm sets `RUNEFOBLE_SPICEDB_ENDPOINT` without a scheme (audit w2-audience-studio F2). Out of scope.

## Product & User Story References
- PRD-0011 (audience interactivity and chaos polls). US-0013.

## Detailed Specification & Implementation Plan
1. Add a JWT verification middleware in the service. It fetches keys from the JWKS URL (`RUNEFOBLE_ZITADEL_JWKS_URL`), checks RS256 signature, `exp`, `iss` (`RUNEFOBLE_ZITADEL_ISSUER`), and `aud` (`RUNEFOBLE_ZITADEL_AUDIENCE`). Use a maintained JOSE library with remote JWKS support. Check its API with Context7 before use.
2. Apply the middleware to every route except `/health` and `/ui/manifest`.
3. Actor identity: every handler reads the subject from the verified token. Delete `dm_user_id` from request bodies and the `x-user-id` header read. Delete the `dm-user` fallback.
4. Delete the `POST /auth/tuples` route and its in-memory write helper.
5. WebSocket connections (if any in this service) authenticate before accept with the subprotocol contract from TASK-0520. The gateway side is TASK-0522.
6. Helm: add the three issuer variables to `audience-studio.yaml`. Coordinate with TASK-0625, which handles the literal key default in the same service.

## Frontdoor Blackbox Test Plan
HTTP tests with the service test runner, using tokens signed by a test key served from a local JWKS.
- Before: `POST /auth/tuples` with no auth returns 201. Approve with `dm_user_id` of a non-DM returns 200.
- After:
  - No bearer, forged token, and expired token return 401 on every route.
  - `POST /auth/tuples` returns 404.
  - Approve with a non-DM token returns 403 (authorization theme enforces the DM check; identity is the token subject).
  - A body `dm_user_id` does not change the actor.

## Definition of Done
1. `grep -rn "dm-user\|dm_user_id\|x-user-id\|/auth/tuples" services/audience_studio/src` returns no production matches.
2. Service test suite passes with the test JWKS.
3. Helm renders the variables.
4. `docs/reference` for audience studio lists the bearer requirement and the removed route.
5. No file exceeds 500 lines.

## Audit Provenance

- Severity: critical
- Source audits: `w2-audience-studio.md`, `w3-authz-coverage.md`
