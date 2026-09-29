---
id: '0500'
title: Remove Backward Compatibility Shims & Re-exports in campaign_analytics
status: Refined
created: 2026-09-29
dependencies:
- TASK-0038
- TASK-0082
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0013
governing_prds:
- PRD-0011
governing_stories:
- US-0014
- US-0038
target_release: 0.9.0
---

# TASK-0500: Remove Backward Compatibility Shims & Re-exports in campaign_analytics

## Status
Refined

## Summary
Decommission backward-compatibility method aliases (`process_domain_event = handle_event` in `worker.py`), legacy tracking property wrappers, and re-export parity tests from `services/campaign_analytics`, migrating all consumers directly to canonical event handling methods.

## Problem Statement
In `services/campaign_analytics/src/campaign_analytics/worker.py`, line 115 retains:
`"""Public alias for handle_event for backward-compatibility."""`
`process_domain_event = handle_event`
Furthermore, `tests/test_campaign_analytics_modular_decomposition.py:test_worker_backward_compatible_properties` actively asserts that `CampaignAnalyticsWorker` maintains backward-compatible tracking properties and helper methods. In a system without active users, maintaining these aliases and writing tests for them incurs waste and violates DoR rule 9.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md`: Combat telemetry and spatial heatmaps.
  - `docs/reference/ports-and-endpoints.md`: Campaign analytics port 8012.
- **Governing Architecture & ADRs**:
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Telemetry projection consumers.
  - **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend component vendoring.

## Product & User Story References
- [`prd-0011-live-audience-chaos-studio-and-spectator-overlay.md`](../../product/accepted/prd-0011-live-audience-chaos-studio-and-spectator-overlay.md)
- [`us-0038-combat-telemetry-and-spatial-heatmaps.md`](../../user_stories/accepted/us-0038-combat-telemetry-and-spatial-heatmaps.md)

## Detailed Specification & Implementation Plan
1. **Remove Worker Method Aliases**:
   - In `services/campaign_analytics/src/campaign_analytics/worker.py`, remove `process_domain_event = handle_event` and any deprecated tracking property wrappers.
   - Ensure all callers invoke `handle_event` directly.
2. **Clean Up `campaign_analytics/__init__.py`**:
   - Prune package root exports to expose only authoritative worker and query classes.
3. **Update Blackbox Test Suites**:
   - In `tests/test_campaign_analytics_modular_decomposition.py`, remove `test_worker_backward_compatible_properties()`.
   - Update all remaining tests to verify telemetry processing through canonical methods.

## INVEST Criteria Evaluation
- **Independent (I)**: Isolated strictly to `services/campaign_analytics` and its test suite.
- **Negotiable (N)**: Clean standard Python class methods.
- **Valuable (V)**: Removes redundant aliases and deletes dead test assertions.
- **Estimable (E)**: Clearly bounded to `worker.py` and one test file.
- **Small (S)**: File changes well under 30 lines.
- **Testable (T)**: Verified via `uv run pytest tests/test_campaign_analytics*`.

## Definition of Done
1. `process_domain_event` alias removed from `worker.py`.
2. All callers migrated to `handle_event`.
3. Obsolete backward-compatibility tests removed from `tests/test_campaign_analytics_modular_decomposition.py`.
4. All campaign analytics tests pass cleanly.
