---
id: '0042'
title: Redis Consumer Groups & Projections Test Suite Decomposition
status: Proposed
created: 2026-09-25
dependencies: [TASK-0015]
governing_adrs: [ADR-0006, ADR-0011]
target_release: 0.2.0
---

# TASK-0042: Redis Consumer Groups & Projections Test Suite Decomposition

## Status
Proposed

## Summary
Decompose monolithic integration test suite `tests/test_redis_consumer_groups.py` (432 lines, 86.4% of limit) into two focused, single-responsibility test modules: one dedicated to low-level consumer group mechanics and DLQ routing, and another dedicated to domain projection workers.

## Problem Statement
Health scans identify `tests/test_redis_consumer_groups.py` as approaching Hard Invariant 6 (File length limit < 500 lines). The file conflates two distinct testing scopes:
1. Low-level distributed messaging mechanics: Stream group creation idempotence, consumer claim recovery, retry counters, Dead Letter Queue (DLQ) threshold routing, and pending entry list (PEL) inspection.
2. High-level domain read projection workers: `SessionReadProjection` event processing across session creation, token movement, tactical encounters, and scene atmosphere updates.

## Proposed Decomposition
1. **Consumer Group Mechanics (`tests/test_redis_consumer_groups.py`)**:
   - Focus exclusively on `RedisConsumerGroup`, consumer worker heartbeats, PEL acknowledgements, and DLQ dispatching (< 250 lines).
2. **Session Read Projections (`tests/test_session_projections.py`)**:
   - Extract `SessionReadProjection` worker tests into a dedicated suite verifying projection state updates upon domain events (< 200 lines).

## Acceptance Criteria
1. Both test files strictly under 250 lines.
2. 100% test pass rate preserved without loss of test coverage or scenario verification.
3. Conforms to Hard Invariant 6 (< 500 lines per file).
