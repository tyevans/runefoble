---
id: '0567'
title: Game Session In-Memory Indexes and Dead Projections Replaced by Durable Queries
status: Complete
created: 2026-11-17
dependencies:
- TASK-0560
- TASK-0565
governing_adrs:
- ADR-0011
- ADR-0007
governing_prds:
- PRD-0014
- PRD-0018
governing_stories:
- US-0044
- US-0058
- US-0073
target_release: 0.9.0
---

# TASK-0567: Game Session In-Memory Indexes and Dead Projections Replaced by Durable Queries

## Status
Complete

## Summary
Game session keeps several index dicts at module level that map a parent id to child ids (bounties, world contracts, settlements, establishments, negotiations). After a restart the aggregates survive but the lists are empty. Separately, `SessionReadProjection`, `PresenceProjection`, and `InitiativeProjection` are never constructed. This task replaces the index dicts with durable queries and deletes the dead projections.

## Problem Statement
- `services/game_session/src/game_session/dependencies.py:122-127` (removed) defines `_session_bounties_index`, `_world_contracts_index`, `_settlement_establishments_index`, `_campaign_settlements_index`, `_establishment_workers_index`, and `_establishment_negotiations_index` as dicts.
- `services/game_session/src/game_session/routers/bounties.py:74` writes the index after save. `:90-91` reads it and suppresses load errors (w1-game-session F3).
- `services/game_session/src/game_session/projections/presence.py:21` (removed) and `projections/session.py:29-44` hold in-memory state. Grep finds no construction site (w1-game-session F10).

## Documentation & Architecture Review
- `complete/0491-remove-backward-compatibility-shims-game-session.md` removes facades only. It does not cover these indexes.
- The durable source is the event store. The list can be built by a query on the aggregate-family event stream, or by a projection table fed by the repository publish path from TASK-0565.

## Product & User Story References
- [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)
- [`us-0073-customizable-establishments-and-assignable-npc-workers.md`](../../user_stories/accepted/us-0073-customizable-establishments-and-assignable-npc-workers.md)
- [`prd-0014-downtime-crafting-and-stronghold-engine.md`](../../product/accepted/prd-0014-downtime-crafting-and-stronghold-engine.md)

## Detailed Specification & Implementation Plan
1. Delete the six index dicts in `dependencies.py`.
2. Add one query function per list (`list_bounties_for_session` and so on) in `game_session/queries/`. Each reads the owning aggregate ids from a persisted index table fed by the repository publish path, or from a family stream query. Pick one approach for all six and document it in the reference doc.
3. Remove `except Exception` around the list queries. Load errors return 503 (see TASK-0561).
4. Delete `projections/presence.py`, `projections/session.py`, and any initiative projection that has no caller. Delete their tests that only exercise the dead code.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** create a session, post a bounty through the public route, restart the app, then `GET .../contracts/bounties`. Before: empty list. After: the bounty is listed.
- **Fail before, pass after:** the same restart test for one settlement and one establishment list.
- No direct access to the index. Assertions use HTTP responses only.

## Definition of Done
1. No module-level index dict remains in `game_session/dependencies.py`.
2. Restart tests above pass.
3. Dead projection modules deleted. `grep -rn SessionReadProjection services` returns none.
4. `uv run pytest` and `make health-check` pass. Files under 500 lines.
5. `CHANGELOG.md` entry.

## Audit Provenance

- Severity: high
- Source audits: `w1-game-session.md`
