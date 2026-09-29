---
id: '0351'
title: Speech-to-Intent Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0002
- TASK-0039
- TASK-0069
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0001
- PRD-0002
governing_stories:
- US-0001
- US-0002
- US-0023
target_release: 0.8.0
---

# TASK-0351: Speech-to-Intent Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_speech_to_intent.py` (271 lines, 54.2% of limit) into modular test submodules under `tests/test_speech_to_intent/` (`conftest.py`, `test_parsing_unit.py`, `test_latency_and_http.py`, `test_redis_streams.py`), ensuring all test modules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tests/test_speech_to_intent.py` combines unit tests for cardinal movement and spell action parsing, sub-200ms latency budget validation benchmarks, FastAPI HTTP route integration tests for The Watcher and Voice Agent microservices, and Redis Streams `PlayerSpokeEvent` dispatch and intent response verification in a single file. As multi-modal speech commands, reaction interrupts, and complex spell parameters expand, this test suite will approach the 500-line limit unless decomposed into focused submodules.

## Governing Architecture & ADRs
- **ADR-0002: Real-Time Audio Streaming Architecture**: Sub-500ms pipeline and sub-200ms parsing latency budget.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout and isolated test execution.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Real-time event propagation and stream broadcasting.
- **ADR-0007: Domain-Driven Design Architecture**: Clean frontdoor testing across service aggregates.
- **ADR-0010: Continuous Integration Pipeline**: Rapid and modular test suite execution.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Shared Fixtures & Test Setup (`tests/test_speech_to_intent/conftest.py`)**:
   - Extract `mock_redis`, `watcher_engine`, and helper client fixtures (< 50 lines).
2. **Intent Parsing Unit Tests (`tests/test_speech_to_intent/test_parsing_unit.py`)**:
   - Extract cardinal movement, melee/ranged attack, spellcasting, and skill check parsing tests (< 100 lines).
3. **Latency Budgets & HTTP Routes (`tests/test_speech_to_intent/test_latency_and_http.py`)**:
   - Extract sub-200ms parsing benchmark tests and FastAPI HTTP integration tests (< 90 lines).
4. **Redis Streams Integration Tests (`tests/test_speech_to_intent/test_redis_streams.py`)**:
   - Extract `PlayerSpokeEvent` ingestion and event broadcast assertions (< 90 lines).
5. **Entry Point Compatibility (`tests/test_speech_to_intent.py`)**:
   - Retain backwards-compatible test runner forwarding or safe migration (< 30 lines).
6. **Verification**:
   - Verify `uv run pytest tests/test_speech_to_intent/` passes with 100% success.

## Definition of Done
- `tests/test_speech_to_intent/` submodules strictly < 110 lines each per Hard Invariant 6.
- 100% pass rate on `uv run pytest tests/test_speech_to_intent/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
