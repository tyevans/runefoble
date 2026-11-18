---
id: '0549'
title: Game Session Settlement, Haggling, Workers, and Bulletin Authorization
status: Refined
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
- PRD-0024
- PRD-0014
governing_stories:
- US-0047
- US-0075
- US-0076
- US-0072
- US-0073
- US-0064
target_release: 0.9.0
---

# TASK-0549: Game Session Settlement, Haggling, Workers, and Bulletin Authorization

## Status
Refined

## Summary
The settlement and haven routes in `game_session` have the widest authorization gap in the service. The shared helper runs its check only `if uid:`, so an anonymous caller passes. Haggling trusts an `X-RuneFoble-Role` header to skip arbitration. Establishment and negotiation routes take identity from a header with no check. This task makes every settlement-scoped route check a schema permission on the settlement, establishment, negotiation, NPC, or bulletin object, and removes the role header.

## Problem Statement
- `services/game_session/src/game_session/settlement/auth/permissions.py:16` (`_enforce`) runs only `if uid:`. It feeds `load_settlement`, `load_establishment`, `load_worker`, and the negotiation checks (`w3-authz-coverage.md` F10).
- `services/game_session/src/game_session/settlements/auth.py:70,88`, `settlement/bulletin_auth.py:20,38,65,86`, `settlement/haven/routes_establishments.py:37`, `routes_havens.py:38`, `routes_upgrades.py:32,55`, `settlement/workers/routes_roster.py:43,95`, `routes_inventory.py:60`, `routes_relationships.py:26,43`, `routers/settlements.py:59,98,122`: all fail open when identity is missing (`w3-authz-coverage.md` rows 197-199, 210-234, 240-243).
- `services/game_session/src/game_session/settlement/haggling_router.py:231-238` (`PATCH .../dm-override`): skips the SpiceDB check when `X-RuneFoble-Role` is `dm`, `dungeon_master`, or `game_master`. Any caller who sends the header bypasses arbitration (`w3-authz-coverage.md` F13, critical).
- `haggling_router.py:76,158` (`POST /establishments/{id}/haggle`, `POST /haggling/start`): identity is an optional header with no SpiceDB check (`w3-authz-coverage.md` rows 216-219).
- `haggling_router.py:196,273` (gambit, accept): check runs only when the helper gets an identity.
- `settlement/bulletin_router.py:113,195,244` (pin, remove, decrypt): fail open with no identity.
- `services/game_session/src/game_session/settlement/auth/relationships.py` and `tokens.py`: writes relations that the schema defines, but the write paths are not checked for failure.

## Documentation & Architecture Review
- ADR-0001: `settlement`, `establishment`, `negotiation`, `npc`, and `bulletin_notice` objects. Use `settlement.manage` and `settlement.upgrade`. Use `establishment.play` for patronage and `establishment.manage` for upgrades. Use `negotiation.arbitrate` for DM override.
- ADR-0007: the settlement context owns settlement and haven objects. Tuples are written by the owning route when the object is created.
- `docs/how-to/build-settlements-and-play-mobile-minigames.md`, `docs/how-to/run-tavern-minigames-and-merchant-haggling.md`, and `docs/how-to/post-and-fulfill-mercenary-bounty-contracts.md` describe these routes. Update the auth text.
- Settlement authority helpers exist in two places: `settlement/auth/` and `settlements/auth.py`. Consolidate to `settlement/auth/` in this task.

## Product & User Story References
- US-0047 (tavern minigames and merchant haggling). US-0075 (haggling with DM arbitration). US-0076 (town bulletin board, civic rumors, bounties). US-0072 and US-0073 (settlement browser and establishments). US-0064 (roster and party assignment for NPC workers).

## Detailed Specification & Implementation Plan
1. Fail closed helpers:
   - `settlement/auth/permissions.py` `_enforce`: no principal raises 401. Remove the `if uid:` branch.
   - `settlements/auth.py` and `settlement/bulletin_auth.py`: same. Move one copy into `settlement/auth/` and delete the other (it is a duplicate, `w1-game-session.md` F12).
2. Haggling:
   - Delete the `X-RuneFoble-Role` check in `dm_negotiation_override`. The route always runs `negotiation.arbitrate`.
   - `start` and `establishment haggle`: require the verified principal and `establishment.play`. Create the negotiation with `negotiation:<id>#participant@user:<principal>` and `negotiation:<id>#establishment@establishment:<eid>`.
   - Gambit and accept: `negotiation.participate`.
   - Identity comes from TASK-0529. Confirm that no `x-user-id` read remains in the routes changed here.
3. Settlement routes:
   - Charter (`routers/settlements.py:59`): `shared_world.discover` or `campaign.play` as the schema allows. Writes `settlement:<id>#founder@user` and `settlement:<id>#campaign@campaign:<cid>`.
   - Upgrade and claim-boon (`settlements.py:98,122`): `settlement.upgrade` and `settlement.use`.
   - Found settlement in a campaign (`routes_havens.py:38`): `campaign.play`.
   - Upgrade tier (`routes_upgrades.py:32`): `settlement.upgrade`. Upgrade establishment (`routes_upgrades.py:55`): `establishment.edit`.
   - Construct establishment (`routes_establishments.py:37`): `settlement.upgrade`.
4. Workers and NPCs: assign, relieve, restock, mood, and relationships use `establishment.manage` (assign, relieve), `npc.manage` (restock, relationships), and `npc.edit_mood` (mood).
5. Bulletin: pin uses `settlement.manage` or `settlement.upgrade` (per the schema comment). Remove uses `bulletin_notice.edit`. Decrypt uses `bulletin_notice.view`.
6. Replace each `contextlib.suppress` around a relation write in `settlement/auth/relationships.py` with a propagated `AuthzWriteError` mapped to 503.

## Frontdoor Blackbox Test Plan
Setup: a shared world, a campaign, a settlement, an establishment, and a worker are created through their public routes. The founder and a patron join through their own routes.
- Before the fix, anonymous `POST /api/v1/settlements/{id}/upgrade-tier` returns 200. After the fix it returns 401.
- A stranger with a valid principal calls the same route: 403. The founder: 200.
- `PATCH /api/v1/haggling/{id}/dm-override` with `X-RuneFoble-Role: dm` from a player returns 403. Before the fix it returns 200.
- The DM with `negotiation.arbitrate` (through the campaign run_session) calls the override: 200.
- A patron calls `POST /api/v1/establishments/{id}/haggle` with no principal: 401.
- A bulletin decrypt by a non-viewer: 403. Setup uses the pin route.

## Definition of Done
1. Frontdoor tests exist in `tests/test_blackbox_settlement_authz.py` and pass against the live harness.
2. No `if uid:`, `if x_user_id`, or `X-RuneFoble-Role` gate remains in `services/game_session/src/game_session/settlement*` or `settlements/`.
3. `settlements/auth.py` and the duplicate in `settlement/bulletin_auth.py` are consolidated. One module exists.
4. The three how-to docs in the Documentation section are updated.
5. `uv run pytest services/game_session` passes. `uv run ruff check services/game_session` passes.
6. No file in the change exceeds 500 lines. `haggling_router.py` is already large; split it along the route groups if this change pushes it over.

## Audit Provenance

- Severity: critical
- Source audits: `w3-authz-coverage.md`, `w1-game-session.md`
