---
id: '0786'
title: Settlement and Outpost Upgrades Have Price Tables and Spend Stored Resources
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0001
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0786: Settlement and Outpost Upgrades Have Price Tables and Spend Stored Resources

## Status
Complete

## Summary
TASK-0778 removed client-set costs. Settlement and West Marches outpost upgrades now record zero cost, because no price table exists. Every upgrade is free.

## Problem Statement
- `services/game_session/src/game_session/settlement/charter_handlers.py`: `upgrade_facility` records gold 0 and materials {}.
- `services/campaign_lore/src/campaign_lore/west_marches_aggregate.py`: `upgrade_outpost` records gold 0 and materials {}.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0001.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add a tier price table for settlement facilities and one for outposts, in the owning context, beside `FACILITY_TIERS`. Document the default prices in the how-to.
2. An upgrade spends the cost from the settlement or outpost stored resources. A shortfall answers 409 and records no event, as strongholds do.
3. Record a multi-campaign contribution model as an open design note in the task record. Do not build it here.

## Frontdoor Blackbox Test Plan
- A settlement upgrade with enough resources charges the table cost and the read model shows the new balance.
- A shortfall answers 409 and records no event.
- The same two checks for an outpost upgrade.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `.audit/work/0778.md` (partial outcome)
