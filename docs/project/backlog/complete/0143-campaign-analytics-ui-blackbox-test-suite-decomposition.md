---
id: '0143'
title: Campaign Analytics UI Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0052
- TASK-0110
governing_adrs:
- ADR-0013
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
target_release: 0.4.0
pr_url: https://github.com/tyevans/runefoble/pull/157
---
# TASK-0143: Campaign Analytics UI Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_campaign_analytics_ui.py` (383 lines, approaching limit) into focused, single-responsibility frontdoor test modules under `tests/test_blackbox_campaign_analytics_ui/` (`test_analytics_dashboard_ui.py`, `test_chronicle_timeline_ui.py`, `test_spatial_heatmaps_ui.py`), ensuring all test files remain < 200 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_campaign_analytics_ui.py` tests damage spatial heatmaps, MVP turn charts, and chronicle timeline navigation in a single file spanning 383 lines. Decomposing it into domain-focused submodules prevents future breaches of Hard Invariant 6 (< 500 lines) and enables parallel test execution.

## Governing Architecture & ADRs
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Component test isolation and public frontdoor verification via Storybook stories and UI manifests.

## Product & User Story References
- **Product Requirement**: [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- **User Stories**:
  - [`us-0040-campaign-combat-telemetry-and-living-timeline.md`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)
  - [`us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md`](../../user_stories/accepted/us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md)

## Detailed Specification & Implementation Plan
1. **Telemetry Dashboard Tests (`tests/test_blackbox_campaign_analytics_ui/test_analytics_dashboard_ui.py`)**:
   - Extract frontdoor tests verifying damage distribution charts, MVP turn metrics, and manifest registration (< 140 lines).
2. **Chronicle Timeline Tests (`tests/test_blackbox_campaign_analytics_ui/test_chronicle_timeline_ui.py`)**:
   - Extract timeline scrubbing, milestone event pagination, and historical memory archive tests (< 140 lines).
3. **Spatial Heatmap Tests (`tests/test_blackbox_campaign_analytics_ui/test_spatial_heatmaps_ui.py`)**:
   - Extract 2D canvas damage density rendering, grid coordinate overlay, and filter control tests (< 140 lines).
4. **Test Deprecation Shim (`tests/test_blackbox_campaign_analytics_ui.py`)**:
   - Replaced by package directory runner or clean migration.

## INVEST Criteria Evaluation
- **Independent (I)**: Pure test suite reorganization with zero impact on production runtime or client packages.
- **Negotiable (N)**: Test categorization boundaries can be adapted.
- **Valuable (V)**: Safeguards repo against Hard Invariant 6 violation and enhances developer feedback speed.
- **Estimable (E)**: Standard pytest suite modularization.
- **Small (S)**: Scope strictly isolated to `tests/test_blackbox_campaign_analytics_ui/`; all files < 150 lines.
- **Testable (T)**: Validated by ensuring 100% of existing analytics UI tests continue to pass.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Test Suite**:
   - `tests/test_blackbox_campaign_analytics_ui/` created with focused submodules.
   - All files strictly < 200 lines.
2. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_campaign_analytics_ui/`.
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
