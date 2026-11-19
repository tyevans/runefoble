---
id: '0871'
title: Auth Service Splits Claims, Token Storage and Session State
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0013
- ADR-0015
governing_prds:
- PRD-0023
governing_stories:
- US-0062
target_bc: frontend
target_release: 0.9.0
---
# TASK-0871: Auth Service Splits Claims, Token Storage and Session State

## Status
Complete

## Summary
`frontend/src/auth/auth-service.ts` has 308 lines and five jobs: a singleton, PKCE sign-in, JWT claim parsing, a refresh timer, and `localStorage` persistence. Split it into focused modules. Keep the public API, so callers do not change.

## Problem Statement
- `frontend/src/auth/auth-service.ts:65-93`: JWT payload parsing and claim extraction. These are pure functions.
- `auth-service.ts:112-130`: class wiring, environment setup, singleton and restore.
- `auth-service.ts:151-243`: sign-in, callback, refresh and logout.
- `auth-service.ts:261-284`: `persistSession` and `clearSession` write the `rf_auth_session` record to `window.localStorage`. `restoreSession` reads it.

## Documentation & Architecture Review
- ADR-0013 (App Shell layout). ADR-0015 (no hidden failure in auth).
- `docs/how-to/authenticate-with-zitadel-oidc.md` describes the sign-in flow. Update any file name it cites.
- Token storage in `localStorage` is a security decision. This task does not change it. See the index.

## Product & User Story References
- PRD-0023. US-0062 (registration, Zitadel auth and profile).

## Detailed Specification & Implementation Plan
1. Add `frontend/src/auth/claims.ts` with the pure decode and claim functions.
2. Add `frontend/src/auth/token-store.ts` with load, save and clear for the `rf_auth_session` record. It keeps the storage-disabled handling.
3. Add `frontend/src/auth/auth-session.ts` with the session state and the refresh timer.
4. Keep `AuthService`, its public methods, and the `AUTH_CALLBACK_PATH` export in `auth-service.ts`. Update its imports only.
5. Do not change the storage key, the token shape or the refresh rule.

## Frontdoor Blackbox Test Plan
- Playwright BDD (TASK-0525 journey): sign in with a real Zitadel session, reload the page, and assert that the session restores.
- Vitest unit tests for `claims.ts` and `token-store.ts`. They use fixed token strings, not live tokens.
- Existing `frontend/test` auth tests pass unchanged.

## Definition of Done
- Each new module is under 150 lines. `auth-service.ts` is under 200 lines.
- Public API and `AUTH_CALLBACK_PATH` are unchanged.
- Playwright BDD and Vitest suites pass.
- `pnpm run build` and `make lint` pass. No file over 500 lines.
- No backward-compatibility shim (DoR 9).

## Audit Provenance
- Severity: medium
- Source audits: `frontend-ui`
