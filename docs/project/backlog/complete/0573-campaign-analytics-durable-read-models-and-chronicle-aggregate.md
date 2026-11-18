---
id: '0573'
title: Campaign Analytics Read Models Served From Durable Storage and Chronicle Aggregate Used
status: Complete
created: 2026-11-17
dependencies:
- TASK-0560
- TASK-0578
governing_adrs:
- ADR-0011
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
target_release: 0.9.0
---

# TASK-0573: Campaign Analytics Read Models Served From Durable Storage and Chronicle Aggregate Used

## Status
Complete

## Summary
Campaign analytics writes rows to PostgreSQL but every query reads Python lists and dicts. A restart loses all projections. The `CampaignChronicleAggregate` exists but the service never calls it. This task serves queries from durable storage, rebuilds the read models from the stream at start-up, and routes milestone and MVP writes through the chronicle aggregate, as Hard Invariant 2 requires.

## Problem Statement
- `services/campaign_analytics/src/campaign_analytics/storage.py:37-40` keeps `spatial_records`, `combatants`, and `milestones` as lists and dicts. Queries in `queries/*.py` read them.
- The only SQL is `create_all` (`storage.py:53`) and `table.insert()` (`storage.py:74-75`). Failed writes log at debug (`storage.py:77`). `combat_perf_table` in `schema.py` is never written (w2-campaign-analytics F5).
- `storage.py:55-56` falls back to memory silently.
- `aggregate.py:55` `CampaignChronicleAggregate` is imported only by tests. `ChronicleMilestoneRecorded`, `CombatTelemetrySnapshotCreated`, and `EncounterMvpAwarded` are never produced in production (w2-campaign-analytics F10).
- The consumer group starts at `"0"` only on first creation, so replay after restart does not rebuild state.

## Documentation & Architecture Review
- `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md` lines 18-19 claim PostgreSQL persistence with an SQLite fallback. SQLite is not supported. Correct the claim with this task.
- `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md` line 22 says the aggregate produces the milestone events. Make the doc true.
- TASK-0458 and TASK-0459 (proposed) add more read models. They depend on this task.

## Product & User Story References
- [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- [`us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md`](../../user_stories/accepted/us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md)

## Detailed Specification & Implementation Plan
1. Create the read-model tables (spatial records, combatants, milestones) in PostgreSQL. Queries read from them. Delete the in-memory lists as sources of truth.
2. Writes that fail raise. The consumer does not acknowledge an event whose projection write failed (the dead-letter policy is in TASK-0578).
3. Route milestone and MVP writes through `CampaignChronicleAggregate` via `AggregateRepository`. The projection update follows the saved event.
4. On start-up, reset the consumer position to the last processed id stored with the read model, not to `"0"`, so replay is idempotent.
5. Delete `combat_perf_table` if unused, or write it. Pick one and document it.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** publish a combat round and damage events through the public stream path (or the public ingest route), restart the service, then `GET` the MVP route for the campaign. Before: empty. After: the MVP is returned.
- **Fail before, pass after:** the milestone list after restart contains the milestone recorded before restart.
- **Fail before, pass after:** a simulated store write failure returns 503 on the query-triggering route, not silent success.
- Public routes only. No direct storage access.

## Definition of Done
1. No query reads an in-memory list.
2. Restart tests pass. Aggregate used for milestone and MVP writes.
3. How-to corrected. Events-schema analytics section matches the code.
4. `uv run pytest` and `make health-check` pass. Files under 500 lines.
5. `CHANGELOG.md` entry.

## Audit Provenance

- Severity: high
- Source audits: `w2-campaign-analytics.md`
