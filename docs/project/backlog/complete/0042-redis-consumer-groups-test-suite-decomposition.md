---
id: '0042'
title: Redis Consumer Groups & Projections Test Suite Decomposition
status: Complete
created: 2026-09-25
dependencies:
- TASK-0015
governing_adrs:
- ADR-0006
- ADR-0008
- ADR-0009
- ADR-0011
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/31
---
# TASK-0042: Redis Consumer Groups & Projections Test Suite Decomposition

## Status
Refined

## Summary
Decompose the monolithic integration test suite `tests/test_redis_consumer_groups.py` (435 lines, 87.0% of limit) into two focused, single-responsibility test modules: one dedicated to low-level distributed consumer group mechanics and Dead Letter Queue (DLQ) routing, and another dedicated to high-level domain read projection workers.

## Problem Statement
Health scans identify `tests/test_redis_consumer_groups.py` (435 lines) as rapidly approaching Hard Invariant 6 (File length limit < 500 lines). The test module conflates two distinct testing boundaries:
1. **Low-level distributed messaging mechanics**: Consumer group auto-creation, consumer claim recovery, retry counters, Dead Letter Queue (DLQ) threshold routing, and pending entry list (PEL) inspection.
2. **High-level domain read projection workers**: `SessionReadProjection` event processing across session creation, token movement, tactical encounters, and scene atmosphere updates.

As analytics pipelines and OTel tracing integrations add further event-driven consumers in Milestone 2, this suite will breach the 500-line ceiling.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors test suite organization without modifying production event bus or domain projection implementations.
- **Negotiable (N)**: Shared test fixtures, mock event bus helpers, and test file naming can be tailored for developer clarity.
- **Valuable (V)**: Prevents CI test file length failures, cleanly isolates infrastructure messaging failures from domain projection defects, and improves test suite parallel execution.
- **Estimable (E)**: Standard pytest test module separation with shared fixtures.
- **Small (S)**: Scope strictly isolated to `tests/test_redis_consumer_groups.py`; both resulting test files remain under 250 lines.
- **Testable (T)**: Existing test assertions execute completely against the public `RedisConsumerGroup` and `SessionReadProjection` interfaces with zero skipped tests.

## Governing Architecture & ADRs
- **ADR-0006**: Redis Streams Event Streaming (distributed consumer groups, consumer acknowledgements, DLQ routing).
- **ADR-0008**: Property and Mutation Testing Strategy (deterministic integration test isolation).
- **ADR-0009**: Code Quality and Linting with Ruff and Pre-Commit (strict file length invariant < 500 lines).
- **ADR-0011**: eventsource-py Core Event Sourcing (event projection workers updating read models).

## Proposed Decomposition
1. **Consumer Group Mechanics (`tests/test_redis_consumer_groups.py`)**:
   - Focus exclusively on `RedisConsumerGroup` lifecycle, consumer claim recovery, pending entry list (PEL) acknowledgements, retry policies, and DLQ dispatching (< 250 lines).
2. **Session Read Projections (`tests/test_session_projections.py`)**:
   - Extract `SessionReadProjection` worker tests into a dedicated suite verifying projection state updates upon domain events (`SessionCreatedEvent`, `TokenMovedEvent`, `SceneAtmosphereUpdatedEvent`) (< 200 lines).

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Test Suite Decomposition**:
   - `tests/test_session_projections.py` created and dedicated to read projection workers.
   - `tests/test_redis_consumer_groups.py` focused cleanly on consumer group infrastructure.
2. **Zero Coverage Loss**:
   - 100% of existing test scenarios and assertions preserved with zero skipped or removed checks.
3. **File Length Compliance**:
   - Both test files strictly < 250 lines (well below the 500-line ceiling).
4. **Blackbox Frontdoor Verification**:
   - 100% pass rate on `uv run pytest tests/test_redis_consumer_groups.py tests/test_session_projections.py`.
5. **Quality Gate Verification**:
   - Passes `uv run ruff check tests/` and `uv run ruff format --check tests/`.
