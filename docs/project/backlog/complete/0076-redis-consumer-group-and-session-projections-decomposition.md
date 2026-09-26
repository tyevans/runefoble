---
id: '0076'
title: Redis Streams Consumer Group Worker and Session Projections Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0015
- TASK-0036
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0009
- ADR-0011
target_release: 0.3.0
pr_url: https://github.com/tyevans/runefoble/pull/98
---
# TASK-0076: Redis Streams Consumer Group Worker and Session Projections Modular Decomposition

## Status
Refined

## Summary
Decompose `libs/runefoble_platform/src/runefoble_platform/consumer_group.py` (344 lines, 68.8% of limit) and `services/game_session/src/game_session/projections.py` (308 lines, 61.6% of limit) into focused, single-responsibility modules to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as OpenTelemetry tracing (TASK-0037) and OpenPanel analytics pipelines (TASK-0038) integrate with consumer workers.

## Problem Statement
`consumer_group.py` currently handles event deserialization, dead-letter queue (DLQ) policies, consumer group heartbeat/registration, and worker loops. Similarly, `game_session/projections.py` contains monolithic projection listeners handling multiple independent projection models (turn order states, combatant initiative snapshots, session presence status, and spectator view feeds).

As upcoming platform enablers TASK-0037 (OpenTelemetry trace context propagation across consumer groups) and TASK-0038 (OpenPanel event forwarding) attach middleware hooks to consumer groups, both files will expand significantly and risk violating Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean separation of platform helper libraries.
- **ADR-0006: Redis Streams Distributed Event Bus**: Consumer group streaming architecture and error policies.
- **ADR-0009: Continuous Backlog Refinement and Technical Debt Management**: Preemptive architectural refactoring.
- **ADR-0011: eventsource-py Core Event Sourcing**: Projection worker decoupling.

## Proposed Decomposition
1. **Redis Streams Worker Infrastructure (`libs/runefoble_platform/src/runefoble_platform/`)**:
   - `event_deserializer.py`: Extract Redis stream payload deserialization and CloudEvents/DomainEvent registry resolution (< 90 lines).
   - `consumer_group.py`: Retain core `RedisConsumerGroupWorker`, dead-letter queues, and auto-claim logic (< 220 lines).
2. **Game Session Projections Sub-package (`services/game_session/src/game_session/projections/`)**:
   - `initiative.py`: Turn order and initiative snapshot projection handlers (< 140 lines).
   - `presence.py`: Participant presence and connection state projections (< 120 lines).
   - `__init__.py`: Clean re-exports maintaining existing import paths (`from game_session.projections import ...`) (< 50 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Decomposes internal worker helpers and projection modules without altering public API contracts or Redis stream group names.
- **Negotiable (N)**: Organization of projection sub-handlers can be tuned per projection domain.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) in core platform libraries and game session read models.
- **Estimable (E)**: Standard module separation into focused handlers and reusable deserialization helpers.
- **Small (S)**: Scope strictly isolated to `consumer_group.py` and `game_session/projections.py`; all resulting files < 230 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_redis_consumer_groups.py tests/test_game_session.py tests/test_blackbox_initiative_tracker.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `libs/runefoble_platform/src/runefoble_platform/consumer_group.py` and `services/game_session/src/game_session/projections.py` decomposed into modular files under 230 lines each.
2. 100% test pass rate across all consumer group and projection test suites.
3. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
4. Zero backwards-incompatible changes to stream consumption or event projection interfaces.
5. Passes `uv run ruff check` and `uv run pytest tests/test_redis_consumer_groups.py`.
