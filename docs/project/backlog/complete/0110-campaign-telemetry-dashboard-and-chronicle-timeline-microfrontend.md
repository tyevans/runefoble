---
id: '0110'
title: Campaign Telemetry Dashboard and Chronicle Timeline Microfrontend
status: Complete
created: 2026-09-26
dependencies:
- TASK-0038
- TASK-0052
- TASK-0082
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0007
- ADR-0011
- ADR-0013
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
target_release: 0.3.0
pr_url: https://github.com/tyevans/runefoble/pull/101
---
# TASK-0110: Campaign Telemetry Dashboard and Chronicle Timeline Microfrontend

## Status
Refined

## Summary
Develop the Lit Web Component microfrontend `<runefoble-campaign-analytics>` within `services/campaign_analytics/ui/` to render post-session combat telemetry heatmaps, party damage/healing distribution charts, historical milestone badges, and an interactive round-by-round chronicle timeline.

## Problem Statement
`services/campaign_analytics` aggregates domain event streams into historical summaries (TASK-0052, PRD-0012). Players, streamers (Devon), and DMs (Evelyn) need an intuitive, responsive visual dashboard to inspect combat highlights, map hotspots, and timeline archives, fulfilling US-0040 and US-0054.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Scaffolding microfrontend packaging inside `services/campaign_analytics/ui/`.
- **ADR-0004: Lit Web Components and Storybook UI**: Strict Shadow DOM encapsulation and Bauhaus design tokens.
- **ADR-0007: Real-Time Voice and Board Synchronization**: Responsive live updates and WebSocket event feeds.
- **ADR-0011: eventsource-py Core Event Sourcing**: Projections from domain events rendered into charts.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Service component boundary exposing `/ui/manifest`.

## Product & User Story References
- **Product Requirement**: [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- **User Stories**:
  - [`us-0040-campaign-combat-telemetry-and-living-timeline.md`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)
  - [`us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md`](../../user_stories/accepted/us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md)

## Detailed Specification & Implementation Plan
1. **Interactive Combat Spatial Heatmaps**:
   - Canvas-based 2D grid overlay showing movement corridors, hazard trigger areas, and knockout coordinates.
   - Dynamic density shading with Bauhaus geometric color scales.
2. **Party Performance Infographics**:
   - Damage dealt vs damage taken distribution bar charts using SVG/CSS tokens.
   - MVP turn awards and milestone achievement badge cards with full dark/light theme contrast.
3. **Living Chronicle Scrubber**:
   - Timeline slider synchronizing turn-by-turn event logs with map position snapshots.
   - Direct click-to-play audio recap snippet triggers.
4. **Storybook Verification & Manifest**:
   - Interactive Storybook stories for victory, total party kill (TPK), and milestone celebration states.
   - Vendored manifest in `services/campaign_analytics/ui/manifest.json`.

## INVEST Criteria Evaluation
- **Independent (I)**: Decoupled presentation component consuming REST/WebSocket data via property bindings.
- **Negotiable (N)**: Chart library vs pure SVG implementation can be tailored.
- **Valuable (V)**: Bridges raw event data into engaging visual feedback for storytellers and players.
- **Estimable (E)**: Follows existing microfrontend patterns established in `services/game_session/ui/` and `services/board_state/ui/`.
- **Small (S)**: Scope strictly isolated to `services/campaign_analytics/ui/`; all files < 200 lines.
- **Testable (T)**: Storybook visual verification and blackbox test suite assertions.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Element**:
   - `<runefoble-campaign-analytics>` component rendered with complete Shadow DOM encapsulation and Bauhaus tokens.
2. **Storybook Stories**:
   - Stories for empty state, active combat telemetry, and historical campaign milestones with zero console errors.
3. **Microfrontend Manifest**:
   - Manifest served at `/ui/manifest` exposing tags, styles, and script entries per ADR-0013.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_campaign_analytics_ui.py` validating component registration, manifest endpoint, and REST data binding.
5. **Quality Gates**:
   - Conforms strictly to Hard Invariant 6 (< 500 lines per file).
   - Passes `pnpm run build` and `uv run pytest tests/test_blackbox_campaign_analytics_ui.py`.
