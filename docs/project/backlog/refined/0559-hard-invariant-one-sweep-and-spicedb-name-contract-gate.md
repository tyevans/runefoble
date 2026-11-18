---
id: '0559'
title: Hard Invariant 1 Sweep and SpiceDB Name Contract Gate
status: Refined
created: 2026-11-17
dependencies:
- TASK-0542
- TASK-0543
- TASK-0544
- TASK-0545
- TASK-0546
- TASK-0547
- TASK-0548
- TASK-0549
- TASK-0550
- TASK-0551
- TASK-0552
- TASK-0553
- TASK-0554
- TASK-0555
- TASK-0556
- TASK-0557
- TASK-0558
- TASK-0534
- TASK-0538
governing_adrs:
- ADR-0001
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0068
- US-0009
target_release: 0.9.0
---

# TASK-0559: Hard Invariant 1 Sweep and SpiceDB Name Contract Gate

## Status
Refined

## Summary
This is the closing task of the SpiceDB authorization theme. The domain tasks remove the fail-open paths and the wrong names in their own bounded contexts. This task adds the gate that stops them from coming back. It adds a static test that checks every literal permission and relation name in production code against the schema. It removes the last role-name branches in Python. The App Shell role checks are removed by TASK-0538. It removes the `game_session` definition once no check uses it.

## Problem Statement
- Without a static gate, a new call with an undefined name passes the unit tests, because only the live harness catches it, and only in tests that exist (`w3-authz-coverage.md` F17).
- The App Shell decides DM capability from role strings: `frontend/src/runefoble-app.ts:67-68` (`isDM` from `['dm','admin','owner']`), and `canManage`, `isGm`, `canLaunch`, `isOwnerOrDm` derived from it. `frontend/src/components/plugins/plugin_registry.ts:108` registers DM-only plugins by role (`w2-app-shell.md` F6). This is Hard Invariant 1 in the client.
- `libs/runefoble_auth/src/runefoble_auth/zitadel.py:93` (`is_admin`) and the admin role mapping remain after TASK-0541 only if identity did not remove them. Verify and remove.
- The `game_session` definition in `libs/runefoble_auth/schema/runefoble.zed` is used by no check after TASK-0548 and TASK-0546. Remove it when the grep in the Definition of Done confirms no use.

## Documentation & Architecture Review
- ADR-0001 and Hard Invariant 1: a role decision goes through the schema. The client shows capabilities from the server.
- ADR-0013 (microfrontends): the App Shell stays decoupled from service internals. The capability flags come from a public gateway route (TASK-0543, `GET /api/v1/campaigns/{campaign_id}/capabilities`).
- ADR-0014: the App Shell change is verified by a Playwright BDD scenario, not by a unit test of a copied helper (`w2-app-shell.md` F12).
- `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md` and `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md` describe view gating. Update them.

## Product & User Story References
- US-0068 (App Shell view audit and API proxying). US-0009 (campaign access control). PRD-0023 (App Shell and campaign hub).

## Detailed Specification & Implementation Plan
1. Static contract test `libs/runefoble_auth/tests/test_production_name_contract.py`:
   - Walk `services/`, `gateway/`, and `libs/` production Python sources (exclude `tests/`).
   - Find string arguments of `check_permission`, `require_zanzibar_permission`, `write_relationship`, `touch_relationship`, `delete_relationship`, and `ACTION_PERMISSIONS` entries, using `ast`.
   - For each literal, assert that the (type, name) pair resolves in the parsed schema (TASK-0542 `contract.py`). Relations resolve as relations and permissions as permissions.
   - The test fails with a list of file, line, and name for every mismatch. It has no allowlist.
2. Remove the remaining role-name branches found by `grep -rn "is_admin\|\"admin\"\|'admin'\|dungeon_master\|game_master" services gateway libs --include=*.py` outside tests and the schema. Each remaining branch is replaced by a schema check or deleted.
3. App Shell role strings are removed by TASK-0538 (step 5). This task does not repeat the change. It confirms the removal with the grep gate in the Definition of Done.
   - Remove `isDM`, `canManage`, `isGm`, `canLaunch`, and `isOwnerOrDm` role-string derivations.
   - Load the campaign capabilities from `GET /api/v1/campaigns/{campaign_id}/capabilities` (TASK-0543). Derive view gating from those booleans.
   - Register DM-only plugins by the `run_session` capability.
   - Keep the server checks authoritative. The client flags only control what is shown.
4. Remove the `game_session` definition from `libs/runefoble_auth/schema/runefoble.zed` if `grep -rn "game_session" services gateway libs --include=*.py` shows no check or write. Update `docs/how-to/define-spicedb-zanzibar-permissions.md`.

## Frontdoor Blackbox Test Plan
- The static contract test is the test. It fails before this task on the names left by earlier mistakes, and passes after.
- The DM-only plugin gating is verified by TASK-0538 (Storybook and BDD). This task only confirms the grep gate.

## Definition of Done
1. `libs/runefoble_auth/tests/test_production_name_contract.py` exists and passes.
2. `grep -rn "isDM\|isOwnerOrDm\|canLaunch" frontend/src` returns nothing.
3. `grep -rn "is_admin" services gateway libs --include=*.py` returns nothing outside tests.
4. The `game_session` definition is removed, and the schema parse test still passes.
5. The App Shell grep gate in item 2 returns no match, and the App Shell build passes (item 6).
6. `pnpm run build` in `frontend/` passes. `make build` passes. `uv run pytest` passes for the full Python suite.
7. `docs/how-to/define-spicedb-zanzibar-permissions.md` and the App Shell how-to docs are updated.
8. No file in the change exceeds 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w3-authz-coverage.md`, `w2-app-shell.md`, `w1-libs.md`
