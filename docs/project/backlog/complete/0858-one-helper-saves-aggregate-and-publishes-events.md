---
id: '0858'
title: One Helper Saves an Aggregate and Publishes Its Events
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---
# TASK-0858: One Helper Saves an Aggregate and Publishes Its Events

## Status
Complete

## Summary
Game session routers repeat the same save-then-publish loop in about 24 files. Four files define a local `_save_and_publish` helper with the same body. `libs/runefoble_platform/src/runefoble_platform/event_publish.py` already has `publish_or_fail`, but nothing shares the save step. The autopilot penalty publish bypasses `publish_or_fail` and only logs a warning on failure. The fix adds one helper in `libs/` and uses it at every call site, including the autopilot path.

## Problem Statement
- Local copies of `_save_and_publish`: `services/game_session/src/game_session/routers/settlements.py:38`, `settlement/bulletin_router.py:38`, `settlement/haggling_router.py:46`, `minigame_tables/service.py:71`.
- Inline loops: `routers/stronghold.py:154-162` and `:182`, `routers/tavern.py` (2 sites), `routers/caravan_trade.py` (2 sites), `routers/west_marches.py`, `the_watcher/routers/stand_in.py` (2), `voice_agent/routers/transcribe.py`, `voice_agent/stt.py`, and others. The grep for `uncommitted_events` finds 24 files.
- `services/game_session/src/game_session/routers/autopilot.py:150-171`: the penalty publish is inside its own `try` and logs on failure. It does not use `publish_or_fail`.
- `libs/runefoble_platform/src/runefoble_platform/event_publish.py:58`: `publish_or_fail` exists.

## Documentation & Architecture Review
- ADR-0011: state changes are saved, then events are published.
- ADR-0015 Context item 4: failures must surface.
- `docs/reference/redis-streams-event-bus.md`: document the helper.
- TASK-0751 (refined) narrows exception handlers in the same routers. Land it first, or coordinate the edits.
- TASK-0754 (refined) changes calls from game_session to The Watcher in `autopilot.py`. Coordinate.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `publish_aggregate_events(bus, stream, events)` in `libs/runefoble_platform/src/runefoble_platform/event_publish.py`. It publishes in order and uses `publish_or_fail`. Keep the `if bus:` guard at each caller.
2. Keep the order of `repo.save` and publish identical to the current code. Check the stream constant at each caller.
3. Replace each local helper and inline loop with the library helper. Delete the local helpers.
4. For the autopilot penalty publish, use the same helper. A publish failure must follow the same rule as other callers.
5. Do not keep a wrapper with the old name.

## Frontdoor Blackbox Test Plan
- Existing settlement, stronghold and tavern blackbox tests that read Redis Stream events. Assert the same stream names and event types.
- Force the bus publish to fail through the Redis test double on one settlement route. Assert the route returns a 503 (not 200) and the aggregate save is visible through the public read route.

## Definition of Done
- One publish helper is used by every listed caller. No local copies remain.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r2/services-backend.md` (F4)
