---
id: '0578'
title: Start or Remove Redis Stream Consumers That Never Run in Deployed Processes
status: Complete
created: 2026-11-17
dependencies:
- TASK-0560
- TASK-0562
governing_adrs:
- ADR-0006
- ADR-0001
- ADR-0007
governing_prds:
- PRD-0010
- PRD-0012
governing_stories:
- US-0010
- US-0039
target_release: 0.9.0
---

# TASK-0578: Start or Remove Redis Stream Consumers That Never Run in Deployed Processes

## Status
Complete

## Summary
Every deployed stream is written and none is read by a running process. Four consumer implementations exist and none runs. Campaign analytics tries to start its consumer and fails silently. The SpiceDB sync listener is never registered. Soundscape has no Redis consumer. The inference worker consumes a stream nothing writes. This task gives each consumer a single start point in its lifespan with logged failures and a `/healthz` status, or removes the consumer when no producer exists.

## Problem Statement
- `services/campaign_analytics/src/campaign_analytics/main.py:45` calls `RedisConsumerGroup(client=bus.client)`. `RedisStreamsEventBus` has no `client` attribute. The `except Exception: pass` at `main.py:50-53` hides it. The worker never starts (w3-event-wiring F2). `worker.py:142-144` acknowledges failed messages after logging (w2-campaign-analytics F6). `worker.py:132-133` logs read errors at debug.
- `libs/runefoble_auth/src/runefoble_auth/listener.py:61` (`register_bus_handlers`) has no caller (w3-event-wiring F5).
- `services/soundscape/src/soundscape/event_handlers.py:155-166` subscribes to the in-process bus only. No Redis consumer exists in soundscape (w2-soundscape F1). This is the consumer that `TASK-0438` depends on. `0438` is refined but does not add it.
- `services/inference_worker/src/inference_worker/redis_consumer.py:91-127` consumes `runefoble.inference.requests`. No producer exists. Failed messages are not acknowledged or dead-lettered (w2-inference-worker F7). `redis_enabled` defaults to `False` (`config.py:58`).
- `libs/runefoble_platform/src/runefoble_platform/analytics/worker.py` (`AnalyticsEventWorker`) and `client.py` have no caller (w2-campaign-analytics F12).
- `gateway/mcp/src/gateway_mcp/dynamic/events.py:14-25` falls back to `RedisStreamsEventBus(client=MockAsyncRedis())`, and the gateway never sets the bus. Dynamic tool events never reach `runefoble:events:system` (w1-gateway-mcp F4). `libs/runefoble_platform/src/runefoble_platform/consumer_group.py:14,168` exports `MockAsyncRedis` from production code (w1-libs F11).

## Documentation & Architecture Review
- `docs/reference/redis-streams-event-bus.md` says projection workers run in production. That is false today. Correct it with this task.
- `docs/how-to/track-analytics-events.md` describes the platform worker as live. Correct it.
- `docs/reference/fastmcp-gateway.md` lists event behavior for dynamic tools. Verify it.

## Product & User Story References
- [`us-0010-redis-streams-domain-event-subscription.md`](../../user_stories/accepted/us-0010-redis-streams-domain-event-subscription.md)
- [`us-0039-encounter-tension-adaptive-scoring-and-foley.md`](../../user_stories/accepted/us-0039-encounter-tension-adaptive-scoring-and-foley.md)

## Detailed Specification & Implementation Plan
1. Add one consumer bootstrap helper in `runefoble_platform` that takes a stream, group, and handler, and returns a supervised task. Start it in each service lifespan. Failures are logged at error level and reported on `/healthz` as `consumers: {name: running|failed}`. The service does not swallow them.
2. Use `bus.get_client()` (public accessor). Delete `bus.client` references.
3. Campaign analytics: start the consumer for the session, session-lifecycle, and combat streams. Acknowledge only after a successful projection write. Failed messages go to a dead-letter stream (use the existing DLQ routing in `consumer_group.py`).
4. Soundscape: add a consumer for `runefoble.events.session`, `runefoble.events.watcher`, and `runefoble.events.character`, routed to `handle_incoming_domain_event`. This unblocks TASK-0438.
5. SpiceDB: call `register_bus_handlers` from the owning service lifespan, or delete the listener and its handlers if the tuple sync is implemented elsewhere. Record the decision in `docs/reference/`.
6. Inference worker: remove the Redis consumer until a producer exists (record the decision; TASK-0448 may reintroduce it with a producer and a dead-letter path).
7. Platform analytics worker: wire it to campaign analytics through the OpenPanel client, or delete it. Record the decision.
8. Gateway MCP: inject the real bus at gateway start-up. Remove the mock fallback and the `MockAsyncRedis` export from production modules. Log dropped events.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** start campaign analytics with a real Redis container. Publish a session event through the public route. Read the analytics `GET` route. Before: no data. After: the projection contains the event.
- **Fail before, pass after:** `/healthz` of campaign analytics reports `consumers.analytics: running`. Before: the service boots with no worker and no status.
- **Fail before, pass after:** a dynamic tool register through the public gateway MCP route appears on `runefoble:events:system` (through a Redis stream reader). Before: no entry.
- **Fail before, pass after:** a soundscape tension update follows a `CombatEncounterStarted` published to Redis through the game session route.
- No mock Redis in any production import (grep).

## Definition of Done
1. Every remaining consumer has one start point, logs failures, and reports status on `/healthz`.
2. Four tests above pass. Each removed consumer has a recorded decision in the reference docs.
3. `grep -rn "bus.client\|MockAsyncRedis" services gateway libs` returns no production hits.
4. `uv run pytest` and `make health-check` pass. Files under 500 lines.
5. `CHANGELOG.md` entry.

## Audit Provenance

- Severity: critical
- Source audits: `w3-event-wiring.md`, `w2-campaign-analytics.md`, `w2-soundscape.md`, `w2-inference-worker.md`, `w1-gateway-mcp.md`, `w1-libs.md`
