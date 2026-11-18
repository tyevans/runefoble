---
id: '0562'
title: Board and Watcher Publish Calls Use the Real Redis Bus API
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0006
- ADR-0002
governing_prds:
- PRD-0005
- PRD-0001
governing_stories:
- US-0014
- US-0010
target_release: 0.9.0
---

# TASK-0562: Board and Watcher Publish Calls Use the Real Redis Bus API

## Status
Complete

## Summary
`RedisStreamsEventBus` exposes `publish_event(stream, event)`. It has no `publish`. Several board-state and watcher call sites call `bus.publish(...)` inside `contextlib.suppress(Exception)`, so the `AttributeError` is hidden and the event never reaches Redis. This task replaces each call with `publish_event` on the named stream, deletes the dead `hasattr` branches, and publishes every uncommitted event through one shared helper in `board_state`.

## Problem Statement
- `services/the_watcher/src/the_watcher/simulation_engine.py:286` calls `bus.publish(STREAM_WATCHER, tick_event)`. World tick events never reach Redis (w1-the-watcher F1, w3-event-wiring F3).
- `services/board_state/src/board_state/routers/aoe.py:105-106`, `routers/actions.py:54-55`, and `routers/uvtt_import.py:30` call `bus.publish(board.uncommitted_events[-1])`. This has the wrong arity and only the last event is attempted (w1-board-state F6).
- `services/board_state/src/board_state/routers/physics.py:30`, `routers/traps.py:37-38`, `routers/tokens.py:61-66` are dead `publish` branches guarded by `hasattr(bus, "publish_event")` ordering. They swallow errors with `except Exception: pass`.
- `services/the_watcher/src/the_watcher/turf_war/service.py:39-51` uses `hasattr` duck typing and calls `bus.publish(STREAM_WORLD, evt)` at line 49.
- `libs/runefoble_platform/src/runefoble_platform/redis_bus.py:41` defines `publish_event` only (verified during synthesis).

## Documentation & Architecture Review
- ADR-0006 requires publishing to Redis Streams with the wire type, event id, and trace context. `publish_event` already does this (w3-event-wiring "Healthy areas").
- `docs/reference/redis-streams-event-bus.md` must state the single publishing rule for board events (see TASK-0565 for the repository rule).
- Existing tests use the in-memory `EventBus`, which has `publish`. That is why the suite passed. The new tests use a Redis-shaped double that exposes only `publish_event`.

## Product & User Story References
- [`prd-0005-realtime-websocket-board-sync.md`](../../product/accepted/prd-0005-realtime-websocket-board-sync.md)
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`us-0014-realtime-board-websocket-sync.md`](../../user_stories/accepted/us-0014-realtime-board-websocket-sync.md)

## Detailed Specification & Implementation Plan
1. Add `publish_board_events(bus, stream, events)` in `services/board_state/src/board_state/events.py` (or the module already used by routers). It calls `publish_event` for each event in order and logs failures with stream and event type. It does not swallow errors. Error policy is handled by TASK-0564.
2. Replace the calls at `aoe.py:105-106`, `actions.py:54-55`, `uvtt_import.py:30`, `physics.py:30`, `traps.py:37-38`, `tokens.py:61-66` with the helper. Delete dead `publish` branches.
3. In `simulation_engine.py:286`, replace `bus.publish` with `bus.publish_event(STREAM_WATCHER, tick_event)`.
4. In `turf_war/service.py:39-51`, remove the `hasattr` branch and call `publish_event(STREAM_WORLD, evt)`.
5. Remove every `contextlib.suppress(Exception)` wrapped around these calls in the touched files. TASK-0564 owns the remaining suppression in other routers.

Files expected: five board_state routers, `events.py`, `simulation_engine.py`, `turf_war/service.py`, plus tests. Under 15 files.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** with a Redis-shaped double that records `publish_event` calls, call `POST /api/v1/boards/{id}/aoe` (or the equivalent route in `aoe.py`). Before: no stream entry. After: one `AoETemplatePlaced` entry on `runefoble.events.board`.
- **Fail before, pass after:** create a board with a UVTT import through its public route. Before: only the last event is attempted. After: every uncommitted event is written in order.
- **Fail before, pass after:** trigger a world tick through `POST /api/v1/watcher/world/tick` (public route). Assert a `world_tick_executed` entry on `runefoble.events.watcher` through the stream reader. Before: none.
- Assertions read the stream through the public test double of the bus. No private attributes.

## Definition of Done
1. No `bus.publish(` call remains in the listed files. `grep -rn "bus.publish(" services` returns none for board_state, the_watcher.
2. Three blackbox tests above pass against the Redis-shaped double.
3. `uv run pytest` and `make health-check` pass. Changed files under 500 lines.
4. `docs/reference/redis-streams-event-bus.md` updated to name `publish_event` as the only publish API.
5. `CHANGELOG.md` `[Unreleased]` entry.

## Audit Provenance

- Severity: critical
- Source audits: `w3-event-wiring.md`, `w1-board-state.md`, `w1-the-watcher.md`
