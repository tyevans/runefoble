---
id: '0854'
title: Stream Consumers Reclaim Messages Left Pending by a Dead Worker
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: platform
target_release: 0.9.0
---
# TASK-0854: Stream Consumers Reclaim Messages Left Pending by a Dead Worker

## Status
Complete

## Summary
`RedisConsumerGroup.auto_claim_pending` exists to reclaim messages that a crashed worker read and did not acknowledge. No production code calls it. A message held by a dead consumer stays pending. The fix wires the method into `StreamConsumer.poll_once` on a fixed cadence. The handlers must be idempotent, because a reclaimed message can run twice.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/consumer_group.py:98`: `auto_claim_pending` is defined.
- Its only caller is `tests/test_redis_consumer_groups.py:166`.
- `libs/runefoble_platform/src/runefoble_platform/stream_consumer.py:100-121` (`_run` and `poll_once`): no reclaim step.

## Documentation & Architecture Review
- `docs/how-to/run-supervised-redis-stream-consumers.md`: describes the consumer lifecycle. Update it.
- ADR-0011: aggregate handlers must be idempotent under redelivery. Check `@handles` methods before you wire the reclaim.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add a setting for the minimum idle time and the reclaim interval, with defaults in `PlatformSettings`. Do not add a fallback that disables reclaim silently.
2. Call `auto_claim_pending` from `StreamConsumer.poll_once` every N polls.
3. Check each consumer handler for idempotency. A redelivered event must not write twice. Add a version check or an event id check where it is missing. List any handler that cannot be made idempotent and stop there.
4. Update the how-to guide.

## Frontdoor Blackbox Test Plan
- Start consumer A on a test stream. Read one message and stop A before the ack.
- Start consumer B with the reclaim idle time set low. Assert B processes the message once.
- Assert the aggregate state after the test shows one effect (the second delivery is a no-op).

## Definition of Done
- Reclaim runs on the live consumer path, not only in tests.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r2/libs.md` (F7)
