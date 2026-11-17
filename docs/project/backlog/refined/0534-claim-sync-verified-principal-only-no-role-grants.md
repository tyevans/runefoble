---
id: '0534'
title: Claim Sync Accepts Only Verified Principals and Grants No Roles From Token Claims
status: Refined
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0521
governing_adrs:
- ADR-0001
- ADR-0007
governing_prds:
- PRD-0023
governing_stories:
- US-0062
- US-0013
target_release: 0.9.0
severity: critical
source_audits:
- w3-authz-coverage.md
- w1-libs.md
---

# TASK-0534: Claim Sync Accepts Only Verified Principals and Grants No Roles From Token Claims

## Status
Refined

## Summary
`POST /api/v1/auth/sync/user` takes a body with `roles` and `is_admin`, requires no authentication, and writes campaign owner and GM relations. The library maps token roles directly to SpiceDB relations. Remove the public route. Remove the claim-to-relation mapping. The sync layer accepts only a verified principal and writes no campaign or system relations.

## Problem Statement
- `gateway/api/src/gateway_api/auth_sync.py:111-131` (`POST /api/v1/auth/sync/user`) has no auth dependency. It passes the body to `sync_user_claims`. Audit w3-authz F2 (critical).
- Probe in the audit: an unsigned token with `sub=forged-dm` and role `dm` gives `campaign:poc-camp#gm` and `#dungeon_master` for `forged-dm`. `run_session` then returns True.
- `libs/runefoble_auth/src/runefoble_auth/sync_tuples.py:48-62` (`resolve_user_claims`) accepts a dict. It trusts `roles` and `is_admin` from the payload. Audit w1-libs F2.
- `libs/runefoble_auth/src/runefoble_auth/sync.py:65-80` writes `campaign#<role>@user` for every role and `gm` when `is_admin`. `sync.py:72-74` maps `is_admin` to GM. This is a role check (Hard Invariant 1).
- `sync_tuples.py:54,60,71` use `decode_token`, which skipped verification. TASK-0520 removes it.

## Documentation & Architecture Review
- ADR-0001: campaign relations are granted by authorized domain actions (invite acceptance, campaign role assignment with `manage`), not by identity claims.
- The routes `POST /api/v1/auth/sync/membership`, `/character-ownership`, and `/token-binding` (`auth_sync.py:147-243`) also write SpiceDB tuples with no authentication. Their permission model belongs to the authorization theme. Flag them there. This task removes only the user-claim route and the claim mapping.
- TASK-0032 (complete) introduced the sync service. Its claim mapping is the defect.

## Product & User Story References
- PRD-0023 and US-0062 (identity). US-0013 (authorization).

## Detailed Specification & Implementation Plan
1. Delete `POST /api/v1/auth/sync/user` from `auth_sync.py`. Do not replace it with another public route.
2. Delete the claim-to-relation mapping in `sync.py` (roles to campaign relations, `is_admin` to GM) and the dict input path in `sync_tuples.py`.
3. Keep only a verified-principal projection in the library: `VerifiedPrincipal` in, a profile record out (user id, username, email). The profile store is handled by the identity profile route (TASK-0521). The library writes no SpiceDB tuples in this path.
4. If `sync.py` or `sync_tuples.py` has no remaining callers after steps 1-3, delete the module and its exports. Do not keep a stub.
5. Update the reference doc that describes the sync (`docs/reference/spicedb-zitadel-identity-sync.md`). State that token claims never grant relations.
6. Product decision to record in the index: if product wants Zitadel project roles to seed default campaign roles, that is a new, reviewed design. It is not this task.

## Frontdoor Blackbox Test Plan
HTTP tests through the gateway `TestClient`.
- Before: anonymous `POST /api/v1/auth/sync/user` with `roles: ["owner"]` returns 200. Then `manage` on the campaign is granted to that user.
- After:
  - The route returns 404 (or 405).
  - A verified token with `roles: ["owner"]` (in the token) does not grant `manage`. Confirm through the public campaign permission route that the user is still denied.
  - No SpiceDB write occurs. Verify through public reads only.

## Definition of Done
1. `grep -rn "sync/user\|is_admin\|resolve_user_claims" gateway libs` returns no matches.
2. `uv run pytest libs tests/test_blackbox_spicedb_auth_sync.py` passes (updated to the new contract).
3. The sync reference doc is corrected.
4. The index report lists the open product question about project-role seeding.
5. No file exceeds 500 lines.

## Orchestrator Addenda (2026-11-17)

Source: `.audit/synth/discovered-round1.md`.

- Tokenless claim sync returns HTTP 401, not 500. `gateway/api/src/gateway_api/auth_sync.py:138` maps every exception to 500 today.
