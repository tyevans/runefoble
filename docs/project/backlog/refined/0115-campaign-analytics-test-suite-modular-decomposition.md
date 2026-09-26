---
id: '0115'
title: Campaign Analytics Test Suite Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0052
- TASK-0110
governing_adrs:
- ADR-0003
- ADR-0005
- ADR-0006
- ADR-0011
target_release: 0.4.0
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
---

# TASK-0115: Campaign Analytics Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_campaign_analytics.py` (442 lines, 88.4% of limit) into three focused, single-responsibility blackbox test modules strictly under 250 lines each to prevent violating Hard Invariant 6 (File length limit < 500 lines) and maintain test suite clarity.

## Problem Statement
`tests/test_blackbox_campaign_analytics.py` currently exercises the full campaign analytics pipeline in a single monolithic test file:
1. HTTP route tests (`/api/v1/analytics/campaigns/{id}/timeline`, `/heatmaps`, `/mvp`).
2. Redis Streams event projection worker tests (`TokenPlaced`, `TokenMoved`, `DiceRolled`, `CombatRoundAdvanced`, `CharacterHealthChanged`, `AbsenteeRecapGenerated`).
3. Database storage queries, spatial aggregations, and MVP ranking calculations.

As additional battlemap heatmaps, multi-session timeline metrics, and chronicle recap test assertions are added, this file will exceed 500 lines unless decomposed into modular suites.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Standardized package testing across workspace services.
- **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: Storage backend integration with PostgreSQL.
- **ADR-0006: Redis Streams Distributed Event Bus**: Testing event ingestion and consumer group projection workers.
- **ADR-0011: eventsource-py Core Event Sourcing**: Blackbox verification of domain event projections.

## Product & User Story References
- **Product Requirement**: [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- **User Stories**:
  - [`us-0040-campaign-combat-telemetry-and-living-timeline.md`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)
  - [`us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md`](../../user_stories/accepted/us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md)

## Detailed Specification & Implementation Plan
1. **API Endpoints Test Suite (`tests/test_blackbox_campaign_analytics_api.py`)**:
   - Tests public REST endpoints on `services/campaign_analytics/main.py`.
   - Validates response schemas, query parameter filtering (session_id, encounter_id), error handling (404 for unknown campaign), and authorization dependencies (< 200 lines).
2. **Worker Event Ingestion Test Suite (`tests/test_blackbox_campaign_analytics_worker.py`)**:
   - Tests `CampaignAnalyticsWorker` event ingestion over Redis Streams.
   - Validates consumer group acknowledgment, multi-stream routing, and event handling for spatial and combat lifecycle events (< 200 lines).
3. **Storage & Aggregations Test Suite (`tests/test_blackbox_campaign_analytics_storage.py`)**:
   - Tests `CampaignAnalyticsStorage` SQL queries and in-memory aggregation fallbacks.
   - Validates spatial damage heatmaps, round-by-round timeline snapshots, and MVP award calculations (< 180 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Test reorganization with zero modifications to production code contracts.
- **Negotiable (N)**: Split boundaries between worker and storage tests can be tailored.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and improves parallel test clarity.
- **Estimable (E)**: Straightforward refactoring of pytest fixtures and test cases.
- **Small (S)**: Scope strictly isolated to `tests/test_blackbox_campaign_analytics.py`.
- **Testable (T)**: Passes `uv run pytest tests/test_blackbox_campaign_analytics*.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Test Decomposition**:
   - `tests/test_blackbox_campaign_analytics.py` replaced by `tests/test_blackbox_campaign_analytics_api.py`, `tests/test_blackbox_campaign_analytics_worker.py`, and `tests/test_blackbox_campaign_analytics_storage.py`.
2. **Strict Line Limit Enforced**:
   - Every decomposed test file is strictly under 250 lines in compliance with Hard Invariant 6.
3. **Coverage & Parity**:
   - 100% of existing test assertions preserved with zero loss in test coverage.
4. **Quality Gates**:
   - Passes `uv run ruff check tests/`, `uv run ruff format --check tests/`, and `uv run pytest tests/test_blackbox_campaign_analytics*.py`.
