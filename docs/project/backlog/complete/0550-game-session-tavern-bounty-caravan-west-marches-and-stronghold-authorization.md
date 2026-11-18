---
id: '0550'
title: Game Session Tavern, Bounty, Caravan, West Marches, Campfire, and Stronghold Authorization
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0541
- TASK-0542
- TASK-0540
- TASK-0529
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0014
- PRD-0018
governing_stories:
- US-0044
- US-0047
- US-0058
- US-0076
target_release: 0.9.0
---

# TASK-0550: Game Session Tavern, Bounty, Caravan, West Marches, Campfire, and Stronghold Authorization

## Status
Complete

## Summary
These routes in `game_session` share one defect. The check runs only when an identity header is present, or the helper returns success when the identity is missing. Caravan and West Marches creation takes identity from an unchecked header. Bounty posting, claiming, and completion fail open. This task applies the same fail-closed rule to each route group, and it binds each group to its schema permission.

## Problem Statement
- Tavern: `services/game_session/src/game_session/routers/tavern.py:73,96,132,201` (`_check_session_auth`). Anonymous callers pass (`w3-authz-coverage.md` rows 202-204).
- Bounties: `routers/bounties.py:63,114,130` (`check_bounty_post`, `check_bounty_claim`, `check_bounty_disburse`) and `contracts/auth.py:25,33,47,57,67,85,90`. All return success with no identity (`w3-authz-coverage.md` rows 165-167).
- Caravans: `routers/caravan_contracts/board.py:30`, `lifecycle.py:67,96,115,140`, `auth.py:32,43,56`, `routers/caravan_trade.py:48,86`. `_check_perm` and `_init` pass with no identity (rows 169-175).
- West Marches: `routers/west_marches.py:51,102` (create shared world, register campaign) take an unchecked header and call no check (rows 205-206). `:137,193,218` (discovery, outpost, notice) pass with no identity (rows 207-209).
- Campfire: `routers/campfire.py:58,71` runs the check only `if x_user_id and not ...` (row 168).
- Stronghold: `routers/stronghold.py:68,98` runs the check only `if x_user_id and not ...` (rows 200-201).

## Documentation & Architecture Review
- ADR-0001: `shared_world.manage` and `shared_world.discover` and `shared_world.trade` for world actions. `caravan_contract.claim`, `fulfill`, and `manage` for contract actions. `bounty_contract.claim`, `fulfill`, `manage`, and `disburse` for bounties. `stronghold.upgrade` and `stronghold.manage` for facilities. `session.participate` for tavern play.
- ADR-0007: the shared-world context owns world and contract objects. The campaign context owns the campaign grant that the world checks read.
- `docs/how-to/run-campfire-rests-and-alchemical-crafting.md`, `docs/how-to/coordinate-west-marches-shared-world-and-caravans.md`, `docs/how-to/charter-frontier-settlements-and-havens.md`, and `docs/how-to/post-and-fulfill-mercenary-bounty-contracts.md` describe these routes. Update the auth text.
- Two caravan auth modules exist (`routers/caravan_contracts/auth.py` and `contracts/auth.py`). Keep one. Delete the other in this task.

## Product & User Story References
- US-0044 (campfire, downtime, crafting). US-0047 (tavern minigames). US-0058 (West Marches shared world and caravans). US-0076 (bounties). PRD-0014 (downtime and stronghold). PRD-0018 (West Marches).

## Detailed Specification & Implementation Plan
1. Every helper in the list returns or raises 401 for a missing principal. Remove every `if x_user_id` and `if user_id` gate on these routes.
2. Tavern: `session.participate` on start, turn, and merchant haggle. Identity comes from TASK-0529.
3. Bounties:
   - Post: `session.participate` and `campaign.play`. Writes `bounty_contract:<id>#creator@user` and the session and campaign relations.
   - Claim: `bounty_contract.claim`. Writes `#claimant@user`.
   - Complete: `bounty_contract.disburse`. A write failure returns 503.
4. Caravans and shared worlds:
   - Create shared world (`west_marches.py:51`): principal required. Writes `shared_world:<id>#guild_officer@user:<principal>`.
   - Register campaign (`west_marches.py:102`): `shared_world.manage` on the world and `campaign.manage` on the campaign.
   - Contract post: `shared_world.trade`. Contract accept, dispatch, ambush, fulfill: `caravan_contract.claim` or `fulfill` per route. Dispatch caravan and complete trade: `shared_world.trade`.
   - Discovery, outpost, tavern notice: `shared_world.discover` for discovery and notice, and `shared_world.manage` for outposts.
5. Campfire (`campfire.py:58,71`) and stronghold (`stronghold.py:68,98`): `campaign.play` on the campaign. Stronghold initialize: `campaign.run_session`. Upgrade: `stronghold.upgrade`.
6. Delete `contracts/auth.py` or `routers/caravan_contracts/auth.py` after moving the used helpers into one module under `routers/caravan_contracts/`. Update imports.

## Frontdoor Blackbox Test Plan
Setup: a campaign, a session, a shared world, a bounty, and a caravan contract are created through public routes. Players and the DM join through role and invite routes.
- Before the fix, anonymous `POST /sessions/{id}/contracts/bounties` returns 200. After the fix it returns 401.
- A player posts a bounty: 200. A player who is not in the session cannot complete it: 403.
- `POST /api/v1/shared-worlds` with no principal: 401. Before the fix it returns 200 when the header is absent.
- Anonymous `POST /api/v1/campaigns/{id}/stronghold/upgrade` returns 401. A spectator gets 403. A player gets 200.
- Campfire rest with no header: 401.

## Definition of Done
1. Frontdoor tests exist in `tests/test_blackbox_downtime_contracts_authz.py` and pass against the live harness.
2. No `if x_user_id` or `if user_id` gate remains in the files listed in the Problem Statement.
3. Exactly one caravan auth module remains.
4. The four how-to docs in the Documentation section are updated.
5. `uv run pytest services/game_session` passes. `uv run ruff check services/game_session` passes.
6. No file in the change exceeds 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w3-authz-coverage.md`
