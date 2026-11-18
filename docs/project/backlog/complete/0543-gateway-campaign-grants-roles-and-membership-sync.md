---
id: '0543'
title: Gateway Campaign Grants, Role Assignment, and Membership Sync Authorization
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0541
- TASK-0542
- TASK-0521
- TASK-0523
- TASK-0534
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0009
- US-0063
- US-0062
target_release: 0.9.0
---

# TASK-0543: Gateway Campaign Grants, Role Assignment, and Membership Sync Authorization

## Status
Complete

## Summary
Any caller can grant a campaign role, including `owner`. Any caller can write membership, character ownership, and token bindings through the gateway. Any caller can post admin seed and invite routes that write `system:runefoble#admin`. This task makes every grant path go through a SpiceDB `manage` check on the campaign, or it removes the public route. It also adds a capability projection for the App Shell. The projection replaces role-name checks in the client (TASK-0559).

## Problem Statement
- `gateway/api/src/gateway_api/routers/campaigns.py:161-170` (`POST /api/v1/campaigns/{campaign_id}/roles`) has no dependency. It writes any role, including `owner`, for any caller (`w1-gateway-api.md` F1). Probe: an anonymous request with `role=owner` returns 200 and then `manage` is allowed for the attacker (`w3-authz-coverage.md` F3).
- `gateway/api/src/gateway_api/auth_sync.py:112-199` exposes `/api/v1/auth/sync/user`, `/membership`, `/character-ownership`, and `/token-binding`. None has an authorization check. The user route trusts body roles (`w3-authz-coverage.md` F2, F3).
- `gateway/api/src/gateway_api/routers/auth/admin.py:22-57` (`/admin/seed`) and `:59-` (`/admin/invite`) are public. They write `system:runefoble#admin` (a type that does not exist in the schema) and return an admin token. The write error is suppressed (`w3-authz-coverage.md` F4).
- `gateway/api/src/gateway_api/routers/auth/registration.py:21-22` writes `campaign:public#viewer` inside `suppress(Exception)`. `viewer` is not a relation (`w1-libs.md` F5).
- `gateway/api/src/gateway_api/routers/auth/__init__.py:69` mounts the admin router unconditionally.
- `frontend/src/runefoble-app.ts:67-68` decides DM capability from role strings. The gateway has no endpoint that returns per-campaign capability flags.

## Documentation & Architecture Review
- ADR-0001 and Hard Invariant 1: grants and checks use `runefoble.zed` only.
- ADR-0007: campaign membership belongs to the campaign context. The gateway routes and checks it. The gateway does not invent grants.
- `docs/how-to/manage-campaign-lifecycle-and-invites.md` describes invites and roles. Update it so that role assignment requires `manage`.
- `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md` is not affected.
- Campaign state is still held in gateway in-memory dicts (`w1-game-session.md` F2). That is owned by the campaign persistence task and is not changed here.

## Product & User Story References
- US-0063 (campaign creation and Zanzibar roles).
- US-0009 (campaign access control).
- US-0062 (registration and profile). The admin seed route is a dev tool. It is removed from the public gateway.

## Detailed Specification & Implementation Plan
1. `POST /api/v1/campaigns/{campaign_id}/roles`:
   - Require the verified principal (TASK-0520) and `ACTION_PERMISSIONS["campaign.manage"]` through `require_zanzibar_permission`.
   - Accept only the roles `dungeon_master`, `game_master`, `player`, `spectator` (an enum in the request schema). Reject `owner` with 422 in this route. Ownership moves only with campaign creation.
   - Write the tuple through the library factory (TASK-0541). A write error returns 503 and is not suppressed.
2. `POST /api/v1/auth/sync/membership`, `/character-ownership`, `/token-binding`: remove these public routes. Membership comes from invite acceptance (`/api/v1/campaigns/join`), character ownership from character creation (TASK-0551), and token binding from login (TASK-0520). Confirm that no frontend or test calls the removed routes. Update the callers.
3. `POST /api/v1/auth/sync/user`: TASK-0534 removes this public route. Do not repeat the removal here.
4. `POST /api/v1/auth/admin/seed` and `/admin/invite`: TASK-0523 removes these routes with the mock token routes. Do not repeat the removal here. After TASK-0523 lands, both return 404.
5. `registration.py`: remove the `campaign:public#viewer` write (lines 21-22). TASK-0523 also edits this file for username roles. Coordinate the merge.
6. Add `GET /api/v1/campaigns/{campaign_id}/capabilities`. It requires the verified principal. It returns booleans `manage`, `run_session`, `play`, and `view`. Each boolean comes from a SpiceDB check (`ACTION_PERMISSIONS`). The App Shell uses these booleans in TASK-0559.
7. Update `docs/reference/ports-and-endpoints.md` and the OpenAPI description for the changed and new routes.

## Frontdoor Blackbox Test Plan
Setup uses public frontdoors and the live harness (`live_spicedb_with_schema`). Identities come from the verified-principal fixture (TASK-0520).
- Before the fix, anonymous `POST /api/v1/campaigns/c1/roles` with `role=owner` returns 200. After the fix it returns 401.
- A player calls `POST /api/v1/campaigns/c1/roles` with `role=dungeon_master` and gets 403. The campaign owner calls it and gets 200. The DM then reads `GET /api/v1/campaigns/c1/capabilities` and sees `run_session: true`.
- `role=owner` returns 422 for the owner.
- `POST /api/v1/auth/sync/membership`, `/auth/sync/user`, `/auth/sync/character-ownership`, and `/auth/admin/seed` return 404 after removal.
- A write failure against a stubbed SpiceDB (live harness down) returns 503 and writes nothing. Before the fix the response is 200.

## Definition of Done
1. The anonymous and player cases in the frontdoor plan behave as stated. Tests live in `tests/test_blackbox_campaign_grants_authz.py`.
2. No route in `gateway/api/src/gateway_api/routers/auth/` writes `system`, `campaign#viewer`, or `campaign#gm`.
3. `GET /api/v1/campaigns/{campaign_id}/capabilities` is in `/openapi.json`.
4. Test setup for grants in the affected existing tests (`tests/test_gateway_auth.py`, `tests/test_blackbox_vtt_bdd_suite.py`, `tests/test_blackbox_soundscape_gateway.py`, `tests/test_blackbox_spicedb_live_grpc.py`) uses the invite or role frontdoor, not a direct tuple write.
5. `uv run pytest` passes for the changed files. `uv run ruff check gateway/api` passes.
6. Docs in `docs/how-to/manage-campaign-lifecycle-and-invites.md` and `docs/reference/ports-and-endpoints.md` match the code.
7. No file in the change exceeds 500 lines. Split `auth_sync.py` if it does.

## Audit Provenance

- Severity: critical
- Source audits: `w3-authz-coverage.md`, `w1-gateway-api.md`, `w1-libs.md`
