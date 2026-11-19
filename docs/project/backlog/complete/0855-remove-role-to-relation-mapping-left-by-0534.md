---
id: '0855'
title: Remove the Role-to-Relation Claim Mapping That TASK-0534 Left in the Auth Lib
status: Complete
created: 2026-11-18
dependencies:
- TASK-0534
- TASK-0721
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: platform
target_release: 0.9.0
---
# TASK-0855: Remove the Role-to-Relation Claim Mapping That TASK-0534 Left in the Auth Lib

## Status
Complete

Decision (orchestrator, 2026-11-18): scope confirmed. TASK-0534 step 2 was never done; this task deletes the role-to-relation claim mapping. It starts after TASK-0721, whose step 4 keeps the claim sync modules unchanged.

## Summary
TASK-0534 is complete. Its step 2 says to delete the claim-to-relation mapping in `sync.py` and the dict input path in `sync_tuples.py`. The public route is gone, but the mapping is still in the library. `sync_membership` maps role names to campaign relations, and the event handlers call it. ADR-0015 (d) says no Zitadel role grants a SpiceDB relation. The fix deletes the mapping and the handlers that have no caller.

## Problem Statement
- `libs/runefoble_auth/src/runefoble_auth/sync_tuples.py:24-40`: `CAMPAIGN_ROLE_RELATIONS` maps `gm`, `dm`, `dungeon_master`, `player`, `spectator`, and `owner` to relations. `normalize_campaign_role` applies it.
- `libs/runefoble_auth/src/runefoble_auth/sync.py:72-90`: `sync_membership` calls `normalize_campaign_role` (line 86).
- `libs/runefoble_auth/src/runefoble_auth/sync_events.py:28` and `:47`: event handlers call `sync_membership` with a role from the event.
- No production caller exists. `gateway/api/src/gateway_api/auth_sync.py` calls only `check_health`. The routes `POST /api/v1/auth/sync/user` and `/membership` are not in the gateway (grep).
- TASK-0721 (refined), step 4, says "do not touch the claim sync modules" and asks the orchestrator to confirm the scope of TASK-0534. This task treats TASK-0534 step 2 as still owed.

## Documentation & Architecture Review
- ADR-0015 (d): claim sync based on roles is removed. No Zitadel role grants a relation.
- Hard Invariant 1: no role check in business logic.
- `docs/reference/spicedb-zitadel-identity-sync.md`: the tuple mapping. Update it.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Delete `CAMPAIGN_ROLE_RELATIONS` and `normalize_campaign_role`.
2. Delete the role argument and the role branch in `sync_membership`. If no caller remains, delete `sync_membership`.
3. Delete the event handlers in `sync_events.py` that map roles, and any handler with no caller.
4. Keep `check_health` and the write helpers only where a caller remains. Do not keep a stub module.
5. Replace the tests that assert role mapping with the test in the frontdoor plan.
6. Confirm the scope with the orchestrator before refinement, because TASK-0721 step 4 says not to touch these modules.

## Frontdoor Blackbox Test Plan
- Sign in as a verified user whose token carries the role `owner` or `dm`. Call the public campaign permission route for `manage`. Assert denied.
- Assert, through the public SpiceDB check, that no campaign relation exists for that user.

## Definition of Done
- The auth lib has no role-name table and no role-to-relation mapping.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r2/libs.md` (F4)
