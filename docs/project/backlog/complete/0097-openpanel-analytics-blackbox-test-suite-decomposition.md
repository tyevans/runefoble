---
id: 0097
title: OpenPanel Analytics Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0038
- TASK-0082
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0009
target_release: 0.3.0
governing_prds:
- PRD-0012
governing_stories:
- US-0040
pr_url: https://github.com/tyevans/runefoble/pull/96
---
# TASK-0097: OpenPanel Analytics Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_openpanel_analytics.py` (354 lines, 70.8% of limit) into two specialized test modules (`tests/test_blackbox_analytics_client.py` and `tests/test_blackbox_analytics_worker.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as campaign chronicle tracking and spectator interaction metrics expand.

## Problem Statement
`tests/test_blackbox_openpanel_analytics.py` currently spans 354 lines and combines multiple test domains:
1. Client privacy sanitization: Profile ID SHA-256 anonymization, PII property masking, and batching HTTP transport mechanics.
2. FastMCP and REST API analytics instrumentation: Request/response timing metrics, event count verification, and endpoint error tracking.
3. Redis Streams worker projection: Event bus consumer loop processing `SessionStarted`, `CombatRoundAdvanced`, and custom gameplay events into OpenPanel payloads.
4. Error resilience: HTTP retry policies, dead-letter queue routing, and Redis consumer group reconnection behavior.

As Milestone 4 introduces spectator interaction analytics (TASK-0051) and campaign chronicle telemetry (TASK-0052), this test suite will expand significantly and risk violating Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test module separation within root test runner.
- **ADR-0006: Redis Streams Distributed Event Bus**: Real-time analytics event ingestion and streaming tests.
- **ADR-0009: Continuous Backlog Refinement and Technical Debt Management**: Preemptive test modularization prior to 500-line invariant violation.

## Proposed Decomposition
1. **Client & Privacy Verification Suite (`tests/test_blackbox_analytics_client.py`)**:
   - SHA-256 profile anonymization and sensitive property filtering.
   - HTTP transport mocking, batch payload formatting, and fast failure modes (< 160 lines).
2. **Event Worker & Stream Projection Suite (`tests/test_blackbox_analytics_worker.py`)**:
   - Consumer group event consumption and domain CloudEvent translation.
   - Redis Streams stream publishing and worker error handling (< 180 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Modularizes blackbox test structure without changing OpenPanel SDK or analytics worker behavior.
- **Negotiable (N)**: Split boundaries between client unit assertions and worker streaming tests can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and improves blackbox test maintainability.
- **Estimable (E)**: Pure pytest partitioning using shared fixtures in `conftest.py`.
- **Small (S)**: Scope isolated strictly to `tests/test_blackbox_openpanel_analytics.py`; all resulting files < 190 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_blackbox_analytics_*.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_blackbox_openpanel_analytics.py` decomposed into focused test suites strictly under 200 lines each.
2. 100% test pass rate across all existing OpenPanel analytics test scenarios.
3. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
4. Maintains blackbox frontdoor interactions via public HTTP endpoints and Redis Streams.
5. Passes `uv run ruff check` and `uv run pytest tests/test_blackbox_analytics_client.py tests/test_blackbox_analytics_worker.py`.
