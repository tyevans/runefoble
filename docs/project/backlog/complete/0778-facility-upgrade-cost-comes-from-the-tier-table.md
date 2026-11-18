---
id: '0778'
title: Facility Upgrade Cost Comes From the Tier Table, Not the Client
status: Complete
created: 2026-11-17
dependencies:
- TASK-0774
governing_adrs:
- ADR-0011
- ADR-0001
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0778: Facility Upgrade Cost Comes From the Tier Table, Not the Client

## Status
Complete

## Summary
Facility upgrades take their gold and material cost from the request body. A player can pay 1 gold for a 700-gold stronghold tier, or name any materials. Settlement and West Marches upgrades accept a client-set cost in the same way.

## Problem Statement
- `services/game_session/src/game_session/stronghold.py` (`upgrade_facility`): `spent_gold = gold_spent if gold_spent > 0 else tier_info["cost_gold"]`, and `materials_spent` replaces the tier materials when it is not empty.
- `services/game_session/src/game_session/routers/stronghold.py:45-50`: `UpgradeStrongholdRequest` carries `gold_spent` and `materials_spent`.
- `services/game_session/src/game_session/routers/settlements.py:109-110` and `settlement/charter_handlers.py:96-112`: settlement upgrades record the client's `gold_spent` and `materials_spent`.
- `services/game_session/src/game_session/west_marches.py:227-244` and `services/campaign_lore/src/campaign_lore/routers/west_marches.py:60-61,216-217`: shared outpost upgrades take the cost from the payload (default 50 gold).
- `gateway/api/src/gateway_api/models.py:36-37` still declares these request fields (dead after the thin-gateway work; remove it if unused).

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0001.
- `docs/how-to/run-campfire-rests-and-alchemical-crafting.md`, `docs/how-to/charter-frontier-settlements-and-havens.md`, `docs/reference/downtime-and-crafting-events.md`.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Each upgrade command takes the facility id only. The tier table (or the settlement and outpost cost tables) sets the gold and materials. The event records the cost that was charged.
2. Remove `gold_spent` and `materials_spent` from the upgrade request models, and set `extra="forbid"` so a client-set cost answers 422.
3. Settlements and outposts: if the design is a contribution model (several campaigns pay toward one tier), make the contribution a separate command that debits the contributor's treasury, and let the upgrade happen when the tier cost is met. Do not let a contribution create gold.
4. Update every test and how-to that sends a cost.

## Frontdoor Blackbox Test Plan
- A stronghold upgrade with enough funds charges exactly the tier cost.
- A request that names `gold_spent` or `materials_spent` answers 422 and records no event.
- The same two checks for a settlement upgrade and a West Marches outpost upgrade.

## Definition of Done
- No upgrade route accepts a cost from the client.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `.audit/work/0774.md` (Discovered)
