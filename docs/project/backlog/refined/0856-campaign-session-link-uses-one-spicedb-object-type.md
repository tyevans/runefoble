---
id: '0856'
title: Campaign Link for a Session Uses One SpiceDB Object Type
status: Refined
created: 2026-11-18
dependencies:
- TASK-0590
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---
# TASK-0856: Campaign Link for a Session Uses One SpiceDB Object Type

## Status
Refined

## Summary
The campaign-to-session link is written to two object types, `session` and `game_session`. ADR-0015 (a) names `game_session#campaign` as the authoritative link. The permission checks read `session`. The two types also define different `observe` rules. The fix writes one object type, moves the checks to it, and removes the second write. The `observe` rules must be made equal first, or access changes.

## Problem Statement
- `libs/runefoble_auth/src/runefoble_auth/sync.py:100-105`: `sync_session_campaign` writes `session#campaign` and `game_session#campaign`.
- `services/game_session/src/game_session/campaign/tuples.py:68`: `link_session` loops over `("session", "game_session")`.
- Checks use `session`: `services/the_watcher/src/the_watcher/dependencies.py:123`, `services/game_session/src/game_session/contracts/auth.py:22` and `:31`.
- `libs/runefoble_auth/schema/runefoble.zed:38-41` (`game_session`): `observe = campaign->view`. `:46-50` (`session`): `observe = campaign->view + participate + control`. The two rules differ.

## Documentation & Architecture Review
- ADR-0015 (a): `game_session#campaign` is the authoritative link.
- ADR-0001: permissions are checked against the schema in `runefoble.zed`.
- TASK-0590 (complete) chose `game_session` as the owner of campaign membership.
- `docs/how-to/define-spicedb-zanzibar-permissions.md` and `docs/reference/spicedb-zitadel-identity-sync.md`: update them.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Change `observe` on `game_session` so that it grants the same access as `session` today (`view + participate + control`). Confirm this in a schema test before any other change. Do not widen access by accident.
2. Move the checks in `the_watcher/dependencies.py` and `game_session/contracts/auth.py` to `game_session`.
3. Write one tuple in `tuples.py` and `sync.py`. Remove the second write.
4. Provide a reconcile step that writes the `game_session#campaign` tuple for existing sessions. Use the public sync path. Do not use a backdoor script.
5. Remove `definition session` from `runefoble.zed` after no caller remains.

## Frontdoor Blackbox Test Plan
- Create a campaign and a session through the public routes. Assert the campaign GM passes `observe`, `participate`, and `control` checks on the session route.
- Assert a user with no campaign role is denied on the same routes.
- Run the schema test that compares the two rules before the change, and after.

## Definition of Done
- One object type holds the campaign link. The checks read it.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r2/libs.md` (F5)
