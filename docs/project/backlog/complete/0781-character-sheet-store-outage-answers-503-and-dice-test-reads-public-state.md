---
id: '0781'
title: Character Sheet Store Outage Answers 503 and the Dice Test Reads Public State
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: character_sheet
target_release: 0.9.0
---

# TASK-0781: Character Sheet Store Outage Answers 503 and the Dice Test Reads Public State

## Status
Complete

## Summary
Some character_sheet write routes catch `Exception` and answer 400 when the event store is down. A store outage is a server fault and must answer 503. One dice-physics test reads the private event list of the in-memory store, which Hard Invariant 7 forbids.

## Problem Statement
- `services/character_sheet/src/character_sheet/routers/` (not created): write routes with `except Exception` that map every failure to 400. Find each with `grep -rn "except Exception" services/character_sheet/src`.
- The dice-settled test under `tests/test_blackbox_*dice*` or `tests/test_blackbox_physics*` reads `store._events` (or the provider seam store) to assert a settled roll.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0014.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Replace broad handlers with typed ones. Domain validation errors answer 400 or 422. `register_store_unavailable_handlers` (from `runefoble_platform.aggregate_loading`) maps store errors to 503.
2. Change the dice test to assert through the public board or roll read model, or through the published standard event on the mock bus.

## Frontdoor Blackbox Test Plan
- With `store_outage()` from `tests/helpers/event_store_seam.py`, each changed write route answers 503 and publishes no event.
- A bad request to the same routes still answers 400 or 422.
- The dice test passes with no reference to a private store attribute.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0773.md` (Discovered)
