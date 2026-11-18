---
id: '0730'
title: Chronicle Milestones Are Idempotent When a Projection Commit Is Replayed
status: Complete
created: 2026-11-17
dependencies:
- TASK-0579
governing_adrs:
- ADR-0011
governing_prds:
- PRD-0012
governing_stories:
- US-0040
target_bc: campaign_analytics
target_release: 0.9.0
---
# TASK-0730: Chronicle Milestones Are Idempotent When a Projection Commit Is Replayed

## Status
Complete

## Summary
The chronicle milestone is saved through the aggregate repository and then written to the read model in a different transaction. A failure between the two writes makes the replay add a second milestone row.

## Problem Statement
- `services/campaign_analytics/src/campaign_analytics/event_handlers.py:69` loads the chronicle aggregate. Line 79 calls `self.chronicle.save(aggregate)`. Line 80 calls `tx.add_milestone(...)`.
- The chronicle repository uses the process-wide event store (`libs/runefoble_platform/src/runefoble_platform/event_sourcing.py`). The projection uses `storage.engine`. The two writes share no transaction.
- `projection.py:155` derives the milestone row id from the `timestamp` argument through `_row_id(...)`. A replay records a new event with a new `occurred_at`, so it gets a new row id and a second row.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011.
- TASK-0688 covers only the `storage.py` fallback. TASK-0579 renames wire types in the same handler file: run after it.
- Record the chosen design in `docs/reference/events-schema.md` (milestone identity) and `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md`.

## Product & User Story References
- PRD-0012
- US-0040

## Detailed Specification & Implementation Plan
1. Derive the milestone row id from the chronicle event id (the id of the saved `recorded` event), not from the timestamp. Use `ON CONFLICT DO NOTHING` on that id.
2. Keep the stream-position commit in the same transaction as the read-model write.
3. If a replay finds the milestone event already saved, reuse the saved event and its id. Do not record a new event.
4. Do not add a test-only failpoint. Prove the retry by replaying the same stream message twice through the public Redis stream.

## Frontdoor Blackbox Test Plan
- Publish one `SessionEnded` event through the public Redis stream. Publish the same message again (redelivery). Read the timeline through the public route. Assert exactly one milestone.
- Restart the consumer between the two deliveries (see TASK-0698 for the subprocess pattern). Assert one milestone.

## Definition of Done
- Row id no longer depends on a timestamp argument.
- Reference doc states the milestone identity rule.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: high
- Source audits: `lore-rules-analytics-sound.md (F1)`
