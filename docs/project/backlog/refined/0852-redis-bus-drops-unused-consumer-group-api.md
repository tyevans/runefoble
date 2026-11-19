---
id: '0852'
title: Redis Bus Drops the Unused Consumer-Group API and Its Raw-Field Fallback
status: Refined
created: 2026-11-18
dependencies:
- TASK-0851
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: platform
target_release: 0.9.0
---
# TASK-0852: Redis Bus Drops the Unused Consumer-Group API and Its Raw-Field Fallback

## Status
Refined

## Summary
`RedisStreamsEventBus` keeps three consumer-group methods. Production code does not call them. Production consumers use `RedisConsumerGroup` through `stream_consumer.py`. The bus also appends raw Redis fields to the result when a JSON decode fails, so a consumer gets a value of the wrong type with no marker. The fix deletes the three methods and the raw-field fallback. Decode failures follow TASK-0851.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/redis_bus.py:107` (`create_consumer_group`), `:119` (`read_group`), `:153` (`acknowledge`): these methods have no production caller.
- The only callers are in `tests/test_redis_streams.py` (about lines 157-219).
- `redis_bus.py:147-150`: on a JSON decode failure with `auto_deserialize` off, the code appends `(msg_id, fields)`. The consumer receives the raw field map.
- Production consumers use `libs/runefoble_platform/src/runefoble_platform/consumer_group.py` through `stream_consumer.py`.

## Documentation & Architecture Review
- `docs/reference/redis-streams-event-bus.md`: the consumer-group ownership and the consumer API. Update it.
- `docs/how-to/run-supervised-redis-stream-consumers.md`: the consumer lifecycle. Check it after the change.
- TASK-0851 defines the decode error type that replaces the fallback.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Delete `create_consumer_group`, `read_group`, and `acknowledge` from `RedisStreamsEventBus`. Delete their imports and exports.
2. Move the test cases that still matter to `tests/test_redis_consumer_groups.py`. Remove the duplicates.
3. Replace the `auto_deserialize` raw-field fallback with a raised `EventDecodeError`, or remove the flag if no caller needs it. Confirm with `grep` first.
4. Do not keep a deprecated alias for the removed methods.

## Frontdoor Blackbox Test Plan
- Publish a non-JSON payload to a test stream through the public bus. Start a `RedisConsumerGroup` consumer. Assert the handler does not run and the failure is recorded.
- Grep test: the bus class has no consumer-group methods.
- Existing publish and consume tests still pass.

## Definition of Done
- `redis_bus.py` has publish and no consumer-group methods.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r2/libs.md` (F2)
