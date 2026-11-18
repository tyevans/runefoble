---
id: '0523'
title: Retire Gateway Mock Token Issuance, Admin Seeding, and Username-Derived Roles
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0521
governing_adrs:
- ADR-0001
- ADR-0005
governing_prds:
- PRD-0023
governing_stories:
- US-0062
- US-0070
target_release: 0.9.0
---

# TASK-0523: Retire Gateway Mock Token Issuance, Admin Seeding, and Username-Derived Roles

## Status
Complete

## Summary
The gateway issues its own tokens. It signs them with a fixed string, accepts any password, and derives DM roles from the username. It also seeds system admins without authentication. Remove every route that mints, refreshes, or seeds identity. Zitadel issues all tokens. Local admin bootstrap moves to the Zitadel wiring task.

## Problem Statement
- `gateway/api/src/gateway_api/routers/auth/tokens.py:15-30` (removed) builds a JWT signed with the literal `runefoble-dev-signature`. Lines 34-45 issue it for any username and password. Roles come from the substrings `dm`, `master`, and `dungeon`. Audit w3-ddd F2, w3-authz F5.
- `tokens.py` `refresh_token` mints `user-refreshed`. `logout_user` does nothing. Audit w2-app-shell F1.
- `gateway/api/src/gateway_api/routers/auth/registration.py:33` (removed) grants `dm` and `player` from the username. Its verification state is in memory.
- `gateway/api/src/gateway_api/routers/auth/admin.py:22-57` (removed) (`POST /api/v1/auth/admin/seed`) has no auth and returns an admin bearer. The SpiceDB write is wrapped in `contextlib.suppress(Exception)` (line 16-17). Audit w1-gateway-api F2, w3-authz F4.
- `admin.py:59` (`POST /api/v1/auth/admin/invite`) has no auth.
- `routers/auth/dev_mail.py:27,53` lets any caller send test mail and clear the mail store.

## Documentation & Architecture Review
- Zitadel is the only token issuer (`docs/project/adrs/accepted/adr-0005-kubernetes-first-infrastructure-with-helm-and-kind.md`).
- `docs/how-to/test-email-signups-with-mailpit.md` describes the gateway test-mail routes and signup verification. Rewrite it in this task.
- Campaign invites are a separate feature (TASK-0475 and the authorization theme). Do not remove campaign invite routes here.

## Product & User Story References
- US-0062 (sign-up and sign-in through Zitadel). Registration moves to the Zitadel hosted sign-up page.
- US-0070 (profile management). The profile route stays.

## Detailed Specification & Implementation Plan
1. Delete from `gateway/api/src/gateway_api/routers/auth/tokens.py` (removed): `POST /api/v1/auth/token`, `POST /refresh`, `POST /logout`, and `_generate_mock_jwt`. Delete the module if it is empty.
2. Delete `registration.py` routes `/register`, `/verify`, `/verify-email`, and `/resend-verification`. Sign-up runs on the Zitadel hosted page, linked from the App Shell login view (TASK-0524).
   - If product needs an in-app sign-up form, that form calls the Zitadel management API from a server-side service account. That is a new task, not this one.
3. Delete `admin.py` routes `/admin/seed` and `/admin/invite`. Delete the `_write_system_relation` helper and the `system` resource writes. Local admin bootstrap is in TASK-0526.
4. Delete `dev_mail.py` routes `/dev/send-test`, `/test-email`, and `DELETE /dev/emails`. Mailpit stays as the SMTP sink for Zitadel. Read mail from the Mailpit API or UI at `/mail`.
5. `routers/auth/__init__.py` mounts only `profile`. Remove the duplicate `auth_router` mounts in `main.py`.
6. Keep `GET` and `PATCH /api/v1/profile` on `require_principal` (TASK-0521). Remove any profile field that came from roles.
7. Regenerate and check `/openapi.json`. The auth paths that remain are only the profile routes.

## Frontdoor Blackbox Test Plan
New file `tests/test_blackbox_auth_routes_retired.py`, using `TestClient(app)` and the OpenAPI document.
- Before: `POST /api/v1/auth/token` with `username=evelyn-dm` returns 200 with DM roles. `POST /api/v1/auth/admin/seed` returns 200 with an admin bearer.
- After:
  - Each retired path returns 404 or 405.
  - `/openapi.json` contains no path under `/api/v1/auth/` except the profile routes.
  - Sending `username=anything` and any password to any remaining route cannot obtain a token.

## Definition of Done
1. All routes listed in steps 1-4 are gone. Verify with `grep -rn "admin/seed\|auth/token\|dev/send-test\|_generate_mock_jwt" gateway`.
2. `uv run pytest tests/test_blackbox_auth_routes_retired.py` passes. Dependent suites that used the mock token are migrated to the signing issuer.
3. `docs/how-to/test-email-signups-with-mailpit.md` describes Zitadel sign-up mail through Mailpit.
4. `docs/reference/ports-and-endpoints.md` no longer lists the removed routes.
5. `uv run ruff check gateway/api` passes. No file exceeds 500 lines.

## Audit Provenance

- Severity: critical
- Source audits: `w3-authz-coverage.md`, `w1-gateway-api.md`, `w2-app-shell.md`, `w3-ddd-architecture.md`, `w1-libs.md`
