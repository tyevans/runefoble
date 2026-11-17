---
id: '0524'
title: App Shell Sign-In Through Zitadel OIDC Authorization Code with PKCE
status: Refined
created: 2026-11-17
dependencies:
- TASK-0523
- TASK-0526
governing_adrs:
- ADR-0004
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0062
target_release: 0.9.0
severity: critical
source_audits:
- w2-app-shell.md
- w3-docs-integrity.md
---

# TASK-0524: App Shell Sign-In Through Zitadel OIDC Authorization Code with PKCE

## Status
Refined

## Summary
Replace the App Shell password form and its local fake session with the OIDC authorization-code flow with PKCE against Zitadel. The client keeps tokens only from Zitadel. Remove the dev fallback, the mock session, the mock signature, and the false "RS256 PKCE" claim that is not yet true.

## Problem Statement
- `frontend/src/auth/auth-service.ts:67` sets `devFallback = true`.
- `auth-service.ts:158-170` (`login()`) posts a username and password to `/api/v1/auth/token`. On any error it calls `createMockSession()` when `devFallback` is true. Audit w2-app-shell F1.
- `auth-service.ts:228-235` (`createMockSession()`) builds an unsigned token with signature `mocksignature`. It grants `dm` when the username contains `dm`.
- `auth-service.ts:203` (`refreshToken()`) falls back to a mock session.
- `frontend/src/router/auth-guard.ts` checks only local state. The fallback sets that state, so the guard passes for any name.
- No PKCE, redirect, code exchange, or JWKS check exists in `frontend/src`. `frontend/src/components/runefoble-user-profile.ts:272` still shows "Zitadel OIDC (RS256 PKCE)".

## Documentation & Architecture Review
- PRD-0023 requires OIDC with PKCE and silent refresh. The Zitadel endpoints come from discovery (`/.well-known/openid-configuration`).
- Runtime settings (issuer, client id, scopes) come from `/runtime-config.json`, which TASK-0526 renders from Helm values. Do not hardcode them.
- ADR-0004 and ADR-0013 require Storybook stories for the login view before composition.
- Tests: TASK-0525 owns the Playwright BDD journeys.

## Product & User Story References
- US-0062 scenario 1: sign-in stores the session and redirects to `#/campaigns`. The credentials are checked by Zitadel.
- PRD-0023 section 1 (authentication and identity flow).

## Detailed Specification & Implementation Plan
1. **PKCE helper (`frontend/src/auth/pkce.ts`, new)**: create a `code_verifier` (43-128 characters, from `crypto.getRandomValues`), its S256 `code_challenge`, a `state`, and a `nonce`. Keep them in `sessionStorage` until the callback.
2. **Login (`auth-service.ts`)**: redirect to the Zitadel authorize endpoint with `response_type=code`, the client id, the redirect URI, scopes `openid profile email offline_access`, and the PKCE values. Remove the password post.
3. **Callback route (`#/auth/callback`)**: check `state`. Exchange the code at the token endpoint with `code_verifier`. Store tokens. Remove the callback parameters from the URL. On any error show an error state and sign out.
4. **Refresh**: use the `refresh_token` grant against Zitadel. On failure, clear tokens and send the user to login. Delete the mock session fallback.
5. **Logout**: clear local tokens and redirect to the Zitadel end-session endpoint with `id_token_hint`. Do not call the deleted gateway logout route.
6. **Guard (`auth-guard.ts`)**: treat a token as present only if it is unexpired by its own `exp`. The server still verifies every call.
7. **Delete**: `devFallback`, `createMockSession`, the `mocksignature` literal, and the role derivation from usernames.
8. **Profile component**: show the provider name from runtime config. Show `username` and `email` from the ID token claims only. Do not show roles as authority.
9. **Login view and modal**: a Storybook story for each state (signed out, redirecting, error, signed in). Zero console errors.

## Frontdoor Blackbox Test Plan
Playwright BDD in TASK-0525 is the frontdoor. Unit tests cover `pkce.ts`.
- Before: any username with any password reaches `#/campaigns`. A failed login creates a mock session.
- After:
  - Sign-in with a valid Zitadel user reaches `#/campaigns` with a Zitadel access token.
  - A wrong password stays on the Zitadel page and never reaches the App Shell with a session.
  - The browser never calls `/api/v1/auth/token`.
  - A callback with a wrong `state` shows an error and stores no token.

## Definition of Done
1. `grep -rn "devFallback\|createMockSession\|mocksignature\|api/v1/auth/token" frontend/src` returns no matches.
2. `pnpm run build` and the frontend unit tests pass.
3. Storybook stories for the login states exist and show zero console errors.
4. `docs/how-to/authenticate-with-zitadel-oidc.md` describes the browser flow (TASK-0520 rewrote the dev sections).
5. No file exceeds 500 lines.

## Orchestrator Addenda (2026-11-17)

Source: `.audit/synth/discovered-round1.md`.

- Delete the `updateUser` fallback that invents user `user-valeros` (`frontend/src/auth/auth-service.ts:86-92`).
