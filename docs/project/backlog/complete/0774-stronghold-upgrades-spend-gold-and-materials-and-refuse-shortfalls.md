---
id: '0774'
title: Stronghold Upgrades Spend Gold and Materials and Refuse Shortfalls
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0774: Stronghold Upgrades Spend Gold and Materials and Refuse Shortfalls

## Status
Complete

## Summary
A stronghold upgrade adds the gold and materials it spends to the treasury and the store, instead of
taking them away. Every upgrade makes the stronghold richer. No command checks for too little gold or
too few materials.

## Problem Statement
- `services/game_session/src/game_session/stronghold.py:121`: `handle_upgraded` does
  `treasury_gold += event.gold_spent`.
- The same handler adds `materials_spent` to `stored_materials`.
- The upgrade command does not refuse an upgrade the stronghold cannot pay for.

## Documentation & Architecture Review
- ADR-0011: the command decides (and refuses); the `@handles` method applies the recorded change.
- `docs/how-to/run-campfire-rests-and-alchemical-crafting.md` (stronghold upgrades).

## Product & User Story References
None. Domain correctness.

## Detailed Specification & Implementation Plan
1. In the upgrade command, compute the cost and refuse with a domain error (HTTP 409 or 422, as the
   other domain refusals in game_session do) when gold or any material is short. Record nothing.
2. In `handle_upgraded`, subtract `gold_spent` and each `materials_spent` quantity.
3. Events already stored keep their fields; the handler change applies on replay. Record in the report
   that existing dev data replays with the corrected arithmetic (no users yet, DoR 9).

## Frontdoor Blackbox Test Plan
- Deposit 500 gold through the public route. Upgrade a facility that costs 200. Read the stronghold:
  treasury is 300, materials reduced.
- With 100 gold, request the 200-gold upgrade: refusal status, treasury unchanged, no upgrade event.

## Definition of Done
- Upgrades spend resources and refuse shortfalls.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `work/0584.md`
