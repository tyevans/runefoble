---
id: '0082'
title: OpenPanel Analytics SDK & Worker Modular Decomposition
status: Refined
created: 2026-09-26
dependencies: [TASK-0038]
governing_adrs: [ADR-0003, ADR-0006, ADR-0009]
target_release: 0.2.0
---

# TASK-0082: OpenPanel Analytics SDK & Worker Modular Decomposition

## Status
Refined

## Summary
Decompose `libs/runefoble_platform/src/runefoble_platform/analytics.py` (431 lines, 86.2% of limit) into single-responsibility modules (`privacy.py`, `client.py`, and `worker.py` within `runefoble_platform.analytics`) to ensure strict adherence to Hard Invariant 6 (File length limit < 500 lines) and improve maintainability.

## Problem Statement
`libs/runefoble_platform/src/runefoble_platform/analytics.py` currently stands at 431 lines. As introduced in TASK-0038, the file bundles three distinct responsibilities:
1. PII anonymization, property scrubbing, and privacy sanitation logic (`anonymize_profile_id`, `sanitize_properties`, `FORBIDDEN_PROPERTY_KEYS`).
2. The asynchronous HTTP OpenPanel client (`OpenPanelClient`) handling event buffering, network dispatches, and mock mode recording.
3. The background Redis Streams consumer worker (`AnalyticsEventWorker`) managing stream subscriptions, consumer group initialization, domain event-to-metric translation, and dead-letter routing.

Any addition of new domain event mappings or telemetry destinations risks pushing this file past the 500-line hard ceiling.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal module layout inside `libs/runefoble_platform` without modifying public tracking APIs or event semantics.
- **Negotiable (N)**: File organization (subpackage `analytics/` vs. sibling modules `analytics_privacy.py`, `analytics_client.py`, `analytics_worker.py`) can be structured for backward compatibility.
- **Valuable (V)**: Prevents hard invariant breaches (<500 lines) and isolates privacy scrubbing from Redis transport and HTTP dispatch logic.
- **Estimable (E)**: Pure code decomposition with well-defined interface boundaries.
- **Small (S)**: Scope strictly isolated to `analytics.py` and its direct imports.
- **Testable (T)**: `uv run pytest tests/test_blackbox_openpanel_analytics.py` verifies 100% test pass rate with zero regression.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace for Python Bounded Contexts.
- **ADR-0006**: Redis Streams Event Bus Infrastructure (consumer group acknowledgments and dead-letter queue routing).
- **ADR-0009**: Code Quality and Linting with Ruff (strict file length limit <500 lines).

## Proposed Decomposition
1. **Privacy & Anonymization Engine (`libs/runefoble_platform/src/runefoble_platform/analytics_privacy.py` or `analytics/privacy.py`)**:
   - `anonymize_profile_id`, `sanitize_properties`, and `FORBIDDEN_PROPERTY_KEYS` (~80 lines).
2. **OpenPanel Client (`libs/runefoble_platform/src/runefoble_platform/analytics_client.py` or `analytics/client.py`)**:
   - `OpenPanelClient` with `track`, `identify`, `clear`, and `close` (~110 lines).
3. **Analytics Event Worker (`libs/runefoble_platform/src/runefoble_platform/analytics_worker.py` or `analytics/worker.py`)**:
   - `AnalyticsEventWorker` with consumer group setup, event mapping, polling loop, and DLQ handling (~210 lines).
4. **Clean Re-export Facade (`libs/runefoble_platform/src/runefoble_platform/analytics.py`)**:
   - Re-export `OpenPanelClient`, `AnalyticsEventWorker`, `anonymize_profile_id`, and `sanitize_properties` to maintain 100% backward compatibility (~30 lines).

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Code Extraction**:
   - Decomposition executed into modular components; original facade preserves full backward compatibility.
2. **File Length Compliance**:
   - Every file within `libs/runefoble_platform/` strictly < 300 lines (well under the 500-line hard invariant ceiling).
3. **Frontdoor Blackbox Verification**:
   - 100% pass rate on `uv run pytest tests/test_blackbox_openpanel_analytics.py`.
4. **Static Analysis & Linting**:
   - Passes `uv run ruff check libs/runefoble_platform` and `uv run ruff format --check libs/runefoble_platform`.
