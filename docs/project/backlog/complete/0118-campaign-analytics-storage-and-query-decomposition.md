---
id: 0118
title: Campaign Analytics Storage and Query Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0052
- TASK-0058
governing_adrs:
- ADR-0003
- ADR-0005
- ADR-0011
target_release: 0.4.0
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
pr_url: https://github.com/tyevans/runefoble/pull/114
---
# TASK-0118: Campaign Analytics Storage and Query Modular Decomposition

## Status
Refined

## Summary
Decompose `services/campaign_analytics/src/campaign_analytics/storage.py` (415 lines, 83.0% of limit) into an engine lifecycle / repository class (`storage.py`) and specialized query modules (`queries/spatial.py`, `queries/mvp.py`, `queries/timeline.py`) to prevent violating Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
`services/campaign_analytics/src/campaign_analytics/storage.py` manages all persistence, SQLAlchemy queries, and in-memory aggregation algorithms across 415 lines:
1. SQLAlchemy async engine initialization, connection pooling, and schema table reflection.
2. Spatial grid aggregation queries and damage heatmap calculations.
3. Turn-by-turn MVP scoring algorithms (damage dealt/taken balance, support utility points).
4. Chronicle timeline query builders, milestone record serialization, and encounter session grouping.

As new analytical read-models (such as party spell slot efficiency and encounter pacing curves) are added, this file will exceed 500 lines.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout within `services/campaign_analytics/`.
- **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: PostgreSQL persistence with connection pooling.
- **ADR-0011: eventsource-py Core Event Sourcing**: Analytical read-model projections from event store streams.

## Product & User Story References
- **Product Requirement**: [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- **User Stories**:
  - [`us-0040-campaign-combat-telemetry-and-living-timeline.md`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)
  - [`us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md`](../../user_stories/accepted/us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md)

## Detailed Specification & Implementation Plan
1. **Spatial & Heatmap Queries (`services/campaign_analytics/src/campaign_analytics/queries/spatial.py`)**:
   - Spatial aggregation functions, grid binning, and heatmap response serialization (< 120 lines).
2. **MVP Scoring & Calculations (`services/campaign_analytics/src/campaign_analytics/queries/mvp.py`)**:
   - Combatant performance scoring, damage/healing metrics, and MVP award calculations (< 120 lines).
3. **Timeline & Milestone Queries (`services/campaign_analytics/src/campaign_analytics/queries/timeline.py`)**:
   - Timeline milestone queries and session event filtering (< 110 lines).
4. **Storage Facade (`services/campaign_analytics/src/campaign_analytics/storage.py`)**:
   - `CampaignAnalyticsStorage` class managing connection pools, transaction contexts, and delegating query execution (< 160 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal storage query architecture without altering public method signatures or database schemas.
- **Negotiable (N)**: File and folder naming for query sub-modules.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and allows adding new queries cleanly.
- **Estimable (E)**: Pure refactoring separating query helper methods from connection lifecycle.
- **Small (S)**: Scope strictly isolated to `services/campaign_analytics/src/campaign_analytics/storage.py`; all resulting files < 170 lines.
- **Testable (T)**: Verified with `tests/test_blackbox_campaign_analytics.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Decomposition Executed**:
   - `services/campaign_analytics/src/campaign_analytics/storage.py` decomposed into `storage.py` and dedicated query modules.
2. **Strict Line Limit**:
   - All modules in `services/campaign_analytics/` strictly under 200 lines in compliance with Hard Invariant 6.
3. **Full Backward Compatibility**:
   - 100% backward compatibility for all public methods on `CampaignAnalyticsStorage` (`record_spatial_position()`, `get_campaign_heatmaps()`, `get_campaign_mvp()`, `get_campaign_timeline()`).
4. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest tests/test_blackbox_campaign_analytics*.py`.
