---
id: '0200'
title: Campaign Analytics Stories Fixtures Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0052
- TASK-0110
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
target_release: 0.7.0
---

# TASK-0200: Campaign Analytics Stories Fixtures Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/campaign_analytics/ui/src/runefoble-campaign-analytics.stories.ts` (322 lines, 64.4% of limit) by extracting embedded mock datasets into `services/campaign_analytics/ui/src/fixtures/campaign-analytics.fixtures.ts`, keeping the story definition file strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`services/campaign_analytics/ui/src/runefoble-campaign-analytics.stories.ts` currently contains 322 lines because large mock payloads (`MOCK_HEATMAP_ACTIVE`, `MOCK_MVP_ACTIVE`, and `MOCK_TIMELINE_ACTIVE`) are hardcoded directly within the story file. This clutters Storybook story definitions and prevents reusing mock telemetry data in unit and integration testing.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Visualizer & Lit Component Architecture**: Clean isolation of Storybook stories from mock data payloads.
- **ADR-0012: Theming Tokens & Bauhaus Design System**: Storybook documentation for telemetry heatmaps and chronicle milestones.
- **ADR-0013: Microfrontend Bounded Context Architecture**: UI encapsulation within `services/campaign_analytics/ui/`.

## Scope of Work
1. **Mock Fixture Module (`services/campaign_analytics/ui/src/fixtures/campaign-analytics.fixtures.ts`)**:
   - Extract `MOCK_HEATMAP_ACTIVE`, `MOCK_MVP_ACTIVE`, and `MOCK_TIMELINE_ACTIVE` into a typed, reusable fixture module (< 120 lines).
2. **Storybook File Modularization (`services/campaign_analytics/ui/src/runefoble-campaign-analytics.stories.ts`)**:
   - Import mock fixtures and retain all existing story exports (`Default`, `HeatmapDensity`, `CombatMVP`, `ChronicleTimeline`) in < 90 lines.
3. **Verification**:
   - Verify Storybook builds and stories render with all telemetry sub-panels functional.
   - Run workspace tests via `uv run pytest`.

## Definition of Done
- `runefoble-campaign-analytics.stories.ts` reduced to < 100 lines.
- Extracted fixture file strictly < 130 lines.
- Storybook stories render without errors or regressions.
