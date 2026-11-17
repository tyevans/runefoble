---
id: '0672'
title: Infrastructure Start-Up Failures Fail Fast Without In-Memory Fallback or Suppression
status: Complete
created: 2026-11-17
dependencies:
- TASK-0578
governing_adrs:
- ADR-0006
- ADR-0011
- ADR-0015
governing_prds:
- PRD-0005
governing_stories:
- US-0010
target_release: 0.9.0
severity: high
source_audits:
- work/0560.md
- work/0611.md
- work/0612.md
- work/0607.md
---

# TASK-0672: Infrastructure Start-Up Failures Fail Fast Without In-Memory Fallback or Suppression

## Status
Complete

## Summary
Three start-up paths hide a failed Redis connection. The platform event bus falls back to an in-memory bus. Two call sites suppress the error with `contextlib.suppress(Exception)`. A deployed service then runs with no working bus and reports success. This task removes the fallback on the Redis path and removes both suppressions.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/event_sourcing.py` (`get_event_bus`, about line 147): when `RedisEventBus` fails to initialize, the function logs a warning and returns `InMemoryEventBus()`. ADR-0015 item 4 forbids in-memory fallbacks in deployed environments.
- `services/board_state/src/board_state/dependencies.py:38`: `with contextlib.suppress(Exception):` wraps the bus initialization. A Redis failure produces no error.
- `services/inference_worker/src/inference_worker/redis_consumer.py:42`: `with contextlib.suppress(Exception):` wraps `xgroup_create`. Every error is hidden, including errors other than "group already exists". The consumer then reads from a stream it may not have grouped.
- Already fixed on main (no action): `get_event_store` raises `EventStoreInitializationError` when PostgreSQL is configured and unreachable.

## Documentation & Architecture Review
- ADR-0015 item 4 and the "Failures are visible" rule: a broken backend returns an error. It never returns a substitute.
- ADR-0006 (Redis Streams): the consumer group is part of the stream contract. Create it once. Ignore only the `BUSYGROUP` reply.
- `docs/reference/redis-streams-event-bus.md`: update the startup behavior paragraph in the same change.

## Product & User Story References
- PRD-0005 and US-0010: domain events reach subscribers. A silent bus breaks that promise.

## Detailed Specification & Implementation Plan
1. `get_event_bus`: when `use_redis_event_bus` is set, let the initialization error propagate. Delete the `InMemoryEventBus` fallback on that path. Keep the in-memory bus only when the flag is off, which is the local test mode.
2. `services/board_state/src/board_state/dependencies.py`: delete the `contextlib.suppress` block. Call the bus provider directly. The service lifespan calls it at start-up, so the pod fails at start-up.
3. `services/inference_worker/src/inference_worker/redis_consumer.py`: replace the suppression with a narrow handler. Catch `redis.exceptions.ResponseError` only when the message contains `BUSYGROUP`. Re-raise every other error.
4. No compatibility flag. No alias for the old behavior.
5. Update `docs/reference/redis-streams-event-bus.md` and the start-up note in `docs/how-to/instrument-services-with-opentelemetry.md` if it describes the fallback.

## Frontdoor Blackbox Test Plan
- Start the board_state app with the Redis flag set and a closed Redis port. The start-up fails with a clear error. No request is served.
- Start the inference worker against a Redis double (network boundary) that returns `WRONGTYPE` for `XGROUP CREATE`. `start()` raises. Against a double that returns `BUSYGROUP`, `start()` succeeds.
- Assert only public outcomes: process exit or raised error, HTTP status, and stream reads through the double.

## Definition of Done
- Tests above pass. `grep -rn "contextlib.suppress(Exception)" services/board_state/src/board_state/dependencies.py services/inference_worker/src` returns nothing.
- No `InMemoryEventBus` import on the Redis-flag path in `event_sourcing.py`.
- Reference doc updated. Changed files under 500 lines.
- `uv run pytest` and `make lint` pass.

## Orchestrator Addenda (2026-11-17)

Source: `.audit/synth/discovered-round1.md`.

- `services/inference_worker/src/inference_worker/redis_consumer.py:130-131`: when `_process_message` raises, the error is logged, no result is published, and the message is not acked. Publish an error result with the correlation id, then ack. Callers wait today with no reply.
- `services/inference_worker/src/inference_worker/redis_consumer.py` (TASK-0501): messages with unknown task types or missing fields are rejected without publish or ack. They stay pending and are redelivered. Publish an error result, then ack (dead-letter policy).
