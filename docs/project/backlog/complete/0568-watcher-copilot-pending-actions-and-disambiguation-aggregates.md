---
id: '0568'
title: Watcher Pending DM Actions, Whispers and Disambiguations as Aggregates
status: Complete
created: 2026-11-17
dependencies:
- TASK-0560
- TASK-0561
- TASK-0564
governing_adrs:
- ADR-0002
- ADR-0011
- ADR-0007
governing_prds:
- PRD-0001
governing_stories:
- US-0017
- US-0021
target_release: 0.9.0
---

# TASK-0568: Watcher Pending DM Actions, Whispers and Disambiguations as Aggregates

## Status
Complete

## Summary
The Watcher keeps DM approval windows, pending vetoes, private whispers, and open disambiguation requests in process memory. A restart or a second replica loses them. This task models each as an event-sourced aggregate saved through `AggregateRepository`, with the timers rebuilt from stored deadlines.

## Problem Statement
- `services/the_watcher/src/the_watcher/copilot.py:26-29` holds `_whispers`, `_pending_actions`, `_timer_tasks`, and `_callbacks`.
- `services/the_watcher/src/the_watcher/disambiguation.py:31,161` holds `_pending`.
- Pending vetoes and approval windows are lost on restart (w1-the-watcher F3). AGENTS.md Hard Invariant 2 is violated.

## Documentation & Architecture Review
- `docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md` and `docs/how-to/resolve-conversational-disambiguation-and-combos.md` describe these flows. Verify them and correct any statement that conflicts.
- `complete/0490-remove-backward-compatibility-shims-the-watcher.md` (TASK-0490) removes shims in `the_watcher`. Coordinate: do not change shim files here.

## Product & User Story References
- [`us-0017-human-dm-veto-and-narrative-copilot-whispers.md`](../../user_stories/accepted/us-0017-human-dm-veto-and-narrative-copilot-whispers.md)
- [`us-0021-conversational-intent-disambiguation-and-combos.md`](../../user_stories/accepted/us-0021-conversational-intent-disambiguation-and-combos.md)

## Detailed Specification & Implementation Plan
1. Create `PendingActionAggregate` (keyed by session id) with commands `propose`, `veto`, `approve`, `modify`, and `expire`. Each command emits a registered event.
2. Create `DisambiguationAggregate` (keyed by session id) with `request` and `resolve` commands.
3. Create `WhisperAggregate` (keyed by session and recipient) for DM whispers.
4. Timers: store `deadline` in the event. On start-up, the service schedules expiry for each open action from the stored deadline. The in-memory timer dict keeps only task handles, not state.
5. Routers call the aggregates through repositories. Delete `_pending_actions`, `_whispers`, `_pending`.
6. Use `publish_or_fail` (TASK-0564) for decision events.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** propose an action through the public speech route, restart the app, then veto it through the public veto route. Before: 404 (action gone). After: 200 and a `WatcherActionVetoed` event on the watcher stream.
- **Fail before, pass after:** open a disambiguation, restart, then resolve it. Before: lost. After: resolved.
- **Fail before, pass after:** an action with a 1-second deadline expires after a restart without a DM decision (observed through the stream).
- No private state is touched.

## Definition of Done
1. No module-level state dict in `copilot.py` or `disambiguation.py` (grep).
2. Three restart tests pass. Event types registered with `@register_event`.
3. Events-schema reference updated for new aggregate events.
4. `uv run pytest` and `make health-check` pass. Files under 500 lines.
5. `CHANGELOG.md` entry.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- services/the_watcher/src/the_watcher/copilot.py approve callback (about line 244) logs callback failures as warnings after the approval event is published. Record the failure on the action or return it to the caller.

## Audit Provenance

- Severity: high
- Source audits: `w1-the-watcher.md`
