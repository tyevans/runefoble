---
id: '0552'
title: The Watcher DM, Intent, Stand-In, and Faction Authorization
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
- ADR-0002
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0001
- PRD-0002
- PRD-0017
governing_stories:
- US-0003
- US-0007
- US-0017
- US-0019
- US-0021
- US-0025
- US-0057
target_release: 0.9.0
severity: critical
source_audits:
- w3-authz-coverage.md
- w1-the-watcher.md
---

# TASK-0552: The Watcher DM, Intent, Stand-In, and Faction Authorization

## Status
Refined

## Summary
The Watcher service uses permission names that the schema does not define. The DM helper therefore errors or denies by accident, and some faction routes return success for an anonymous caller. Many DM-only routes (scene generation, encounter spawn, NPC turn, narration, world tick, skirmish, factions) and player-facing intent routes have no check. This task moves every Watcher check to a schema permission, makes each DM-only route require `campaign.run_session` or `session.control`, and makes each player route require `session.participate`.

## Problem Statement
- `services/the_watcher/src/the_watcher/dependencies.py:126-147`: checks `campaign.dungeon_master` and `campaign.owner` (relations), and `session.run_session`, `session.dungeon_master`, `game_session.run_session` (not defined on those types). Errors are not handled in `check_dm_authorization`, so schema errors surface as 500s (`w1-libs.md` F5, `w3-authz-coverage.md` F16).
- `services/the_watcher/src/the_watcher/dependencies.py:56` reads `platform_settings.spicedb_token`. The attribute does not exist, so the factory raises `AttributeError` (`w3-ddd-architecture.md` F8). TASK-0541 replaces this factory.
- `routers/copilot/actions.py:83,123,162` and `routers/copilot/whispers.py:74,114` use `_assert_dm_permission` with the same relation names. These routes fail closed on a missing identity (`w3-authz-coverage.md` healthy areas) but use names that error on a real SpiceDB.
- `routers/faction_resources.py:77,93,124`, `routers/factions.py:64,81`, `routers/turf_war.py:60`: `_assert_dm` and `_assert_dm_permission` return success when the caller is `None` (`w3-authz-coverage.md` rows 269-276, 285-286).
- Unguarded mutating routes (`w3-authz-coverage.md` rows 257-262, 278-284): `routers/autonomous_dm.py:30,50,72,94` (scenes, encounter spawn, NPC turn, narrate), `routers/chronicle.py:19` (recap), `routers/copilot/actions.py:56` (propose), `routers/intent/compound.py:27,67`, `routers/intent/disambiguation.py:142`, `routers/intent/speech.py:31` (transcribe and act, intent), `routers/stand_in.py:27,109`.
- The gateway proxy for `POST /api/v1/watcher/speak-and-act` has no check. Its fix is in TASK-0544.

## Documentation & Architecture Review
- ADR-0001: DM actions check `session.control` (the session is the play object). Player actions check `session.participate`. Read-only views check `session.observe`. Campaign-scoped actions check `campaign.run_session` or `campaign.play`.
- ADR-0002 (event-driven Watcher): the Watcher reacts to events. Its HTTP routes are the frontdoor for DM and player commands. Checks belong on the HTTP frontdoor.
- The Watcher service keeps domain state in memory (`w1-the-watcher.md` F3). This is out of scope and owned by the persistence task. This task changes checks only.
- `docs/how-to/add-a-watcher-ai-tool.md` and `docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md` describe these routes. Update the auth text.

## Product & User Story References
- US-0017 (DM veto and copilot whispers). US-0007 (autonomous DM). US-0003 (DM adjudicates with AI). US-0019 (ad hoc NPC spawning). US-0021 (intent disambiguation and combos). US-0025 (stand-in tactical policies). US-0057 (faction agendas). PRD-0017 (factions).

## Detailed Specification & Implementation Plan
1. `dependencies.py`. The principal comes from TASK-0529. This task changes the permission names and the fail-open branches:
   - One helper `require_session_permission(session_id, permission)` and one helper `require_campaign_permission(campaign_id, permission)`. Each calls `check_permission` with a name from `ACTION_PERMISSIONS`.
   - Remove the `if not caller: return` branches. Missing principal returns 401.
   - Remove the relation names and the `game_session` and `session.run_session` checks.
   - Replace the factory with the library factory (TASK-0541).
2. Permission map (apply to the routes in the Problem Statement):
   - DM-only, session-scoped (`session.control`): scene generate, encounter spawn, NPC turn, narrate, skirmish simulate, faction resource adjust, bribery resolve, mercenary recruit, veto, approve, modify, whispers create and generate, world tick (`campaign.run_session` because the tick is campaign-wide), faction create (`campaign.run_session`).
   - Player-facing (`session.participate`): intent parse, intent execute, intent resolve, transcribe-and-act, intent, propose, stand-in act. Each action inside intent execute still checks the acting character's `character.edit` through the compound action handler.
   - Read-only (`session.observe` or `campaign.view`): chronicle recap, stand-in recap.
3. For each DM route, the DM check is the only check that decides authority. Do not add a role-name check.
4. Propagate `AuthzUnavailableError` as 503 and `AuthzSchemaError` as 500 with a logged error id. Do not map them to 403.

## Frontdoor Blackbox Test Plan
Setup: a campaign, a session, and a faction are created through public routes. The DM joins with `dungeon_master` through the role route. A player joins through invite.
- Before the fix, anonymous `POST /api/v1/campaigns/{id}/factions` returns 200. After the fix it returns 401.
- A player calls `POST /api/v1/factions/{id}/resources/adjust`: 403. The DM: 200.
- A player calls `POST /api/v1/watcher/encounters/spawn`: 403. The DM: 200.
- A player calls `POST /api/v1/watcher/intent` for their own character: 200. For another player's character: 403.
- The DM veto through `POST /api/v1/watcher/veto` by a player: 403. The test also asserts that the response does not come from a schema error (no 500 body).
- With a stubbed SpiceDB outage, `POST /api/v1/watcher/veto` returns 503.

## Definition of Done
1. Frontdoor tests exist in `tests/test_blackbox_watcher_authz.py` and pass against the live harness.
2. `grep -rn "dungeon_master\|game_session\|run_session" services/the_watcher/src/the_watcher/dependencies.py` returns only `ACTION_PERMISSIONS` names that exist in the schema.
3. No `if not caller: return` branch remains in the_watcher routers.
4. The two how-to docs above are updated.
5. `uv run pytest services/the_watcher` passes. `uv run ruff check services/the_watcher` passes.
6. No file in the change exceeds 500 lines. `dependencies.py` is split if it grows past the limit.
