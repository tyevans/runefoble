---
id: 0015
title: Distributed Redis Streams Consumer Groups & Event Projection Workers
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0001, TASK-0007, TASK-0010]
governing_adrs: [ADR-0006, ADR-0007, ADR-0011]
target_release: 0.1.0
governing_prds:
- PRD-0005
governing_stories:
- US-0014
---

# TASK-0015 — Distributed Redis Streams Consumer Groups & Event Projection Workers

## Status
Complete

## Summary
Implemented high-reliability distributed Redis Streams consumer groups, pending message recovery (`XAUTOCLAIM`), Dead Letter Queue (`{stream}.dlq`) poison pill containment, and background event projection workers for denormalized read models across bounded contexts (US-0010, ADR-0006).

## Scope & Key Changes
1. **Consumer Group Client (`libs/runefoble_platform/src/runefoble_platform/consumer_group.py`, `redis_bus.py`)**:
   - Implemented `RedisConsumerGroup`:
     - `create_group`: Idempotent consumer group creation with `BUSYGROUP` handling.
     - `read_group`: Horizontal load balancing across competing consumer workers using `XREADGROUP >` with automated `deserialize_event` deserialization.
     - `ack`: Message acknowledgment via `XACK`.
     - `auto_claim_pending`: Autonomous recovery of stuck or stalled worker messages using `XAUTOCLAIM`.
     - `route_to_dead_letter`: Quarantine of corrupt/poison messages into `{stream}.dlq` with failure metadata envelopes.
   - Enhanced `MockAsyncRedis` with pending entries list (PEL), competing consumer distribution, and auto-claim mechanics for unit testing without live Redis.
   - Kept `consumer_group.py` strictly under 350 lines (302 lines) and `redis_bus.py` at 150 lines (Hard Invariant 6).
2. **Event Projection Worker (`services/game_session/src/game_session/projections.py`)**:
   - Implemented `SessionReadProjection` class maintaining low-latency denormalized read views (`SessionReadModel`, `TokenReadModel`, `AtmosphereReadModel`, `EncounterReadModel`).
   - Projects stream events (`TokenPlaced`, `TokenMoved`, `TokenRemoved`, `SceneAtmosphereSet`, `EncounterSpawned`, `AutonomousActionResolved`, `TurnAdvanced`, `SessionStarted`, `SessionEnded`).
   - Implemented async process loop with graceful start/stop shutdown and poison message DLQ routing.
   - Kept `projections.py` strictly under 300 lines (260 lines) (Hard Invariant 6).
3. **Tests (`tests/test_redis_consumer_groups.py`)**:
   - Tested idempotent consumer group creation.
   - Tested competing consumers dividing messages with zero partition overlap.
   - Tested single and batch message acknowledgment with PEL cleanup.
   - Tested auto-claiming of pending messages from stalled consumers.
   - Tested Dead Letter Queue routing with failure envelopes.
   - Tested `SessionReadProjection` applying events and worker loop execution with fault isolation.
4. **Documentation**:
   - Authored Diataxis reference guide `docs/reference/redis-streams-event-bus.md`.
