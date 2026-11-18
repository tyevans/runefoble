---
id: '0569'
title: Watcher World Tick Counter and Faction Registry as Durable Aggregate State
status: Complete
created: 2026-11-17
dependencies:
- TASK-0560
- TASK-0562
governing_adrs:
- ADR-0011
- ADR-0007
governing_prds:
- PRD-0017
governing_stories:
- US-0057
target_release: 0.9.0
---

# TASK-0569: Watcher World Tick Counter and Faction Registry as Durable Aggregate State

## Status
Complete

## Summary
The world simulation keeps its tick counter, faction registry, tick history, and latest bulletins in module-level dicts. The tick event is also never published (fixed by TASK-0562). This task moves the counter and the registry into `FactionAggregate` and the tick record into the event stream, so that a restart resumes the simulation where it stopped.

## Problem Statement
- `services/the_watcher/src/the_watcher/simulation_engine.py:45-47` holds `_campaign_factions`, `_campaign_ticks`, and `_latest_bulletins`. The tick counter and faction list live outside `FactionAggregate` (w1-the-watcher F3).
- `simulation_engine.py:285-286` drops the `WorldTickExecuted` event (TASK-0562 owns the publish fix).
- After a restart the tick counter resets to zero and factions disappear, so agendas run from the start again.

## Documentation & Architecture Review
- `docs/how-to/simulate-npc-faction-agendas-and-world-ticks.md` describes ticks and bulletins. Check it before coding.
- `proposed/0240-faction-simulation-engine-modular-decomposition.md` splits `simulation_engine.py`. Coordinate file ownership. This task does not split files.

## Product & User Story References
- [`us-0057-autonomous-npc-faction-agendas-and-world-simulation.md`](../../user_stories/accepted/us-0057-autonomous-npc-faction-agendas-and-world-simulation.md)
- [`prd-0017-autonomous-npc-faction-agendas-and-world-simulation.md`](../../product/accepted/prd-0017-autonomous-npc-faction-agendas-and-world-simulation.md)

## Detailed Specification & Implementation Plan
1. Add `tick_count` and `registry` fields to `FactionAggregate` (or a `CampaignWorldAggregate` keyed by campaign id) and an `executed` command that records a `WorldTickExecuted` event.
2. Latest bulletins are read from the aggregate or a projection built from the stream. Delete `_latest_bulletins`.
3. Replace `_campaign_factions` and `_campaign_ticks` with repository loads and saves.
4. Add a restart test to the simulation test suite through the public tick route.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** register a faction, run two ticks through `POST /api/v1/watcher/world/tick`, restart the app, then run one more tick. Before: the response reports tick 1. After: tick 3.
- **Fail before, pass after:** the stream contains three `world_tick_executed` entries after the sequence.
- Public routes and stream only.

## Definition of Done
1. No module-level campaign dict in `simulation_engine.py`.
2. Restart and stream tests pass.
3. Reference docs for `WorldTickExecuted` match the emitted type.
4. `uv run pytest` and `make health-check` pass. Files under 500 lines.
5. `CHANGELOG.md` entry.

## Audit Provenance

- Severity: high
- Source audits: `w1-the-watcher.md`, `w3-event-wiring.md`
