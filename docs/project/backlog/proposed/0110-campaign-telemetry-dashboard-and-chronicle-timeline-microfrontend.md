---
id: '0110'
title: Campaign Telemetry Dashboard and Chronicle Timeline Microfrontend
status: Proposed
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
target_release: 0.4.0
---

# TASK-0110: Campaign Telemetry Dashboard and Chronicle Timeline Microfrontend

## Status
Proposed

## Summary
Develop the Lit Web Component microfrontend `<runefoble-campaign-analytics>` within `services/campaign_analytics/ui/` to render post-session combat telemetry heatmaps, party damage/healing distribution charts, historical milestone badges, and an interactive round-by-round chronicle timeline.

## Problem Statement
`services/campaign_analytics` aggregates domain event streams into historical summaries (TASK-0052, PRD-0012). Players, streamers (Devon), and DMs (Evelyn) need a rich, privacy-preserving visual dashboard to inspect combat highlights, map hotspots, and timeline archives, fulfilling US-0040 and US-0054.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace (`services/campaign_analytics`).
- **ADR-0004**: Lit Web Components and Storybook UI (Shadow DOM, Bauhaus tokens).
- **ADR-0007**: API Gateway Architecture (`/api/v1/analytics/...`).
- **ADR-0011**: eventsource-py Core Event Sourcing (projections from domain events).
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring (`services/campaign_analytics/ui/`).

## Scope of Work
1. **Interactive Combat Spatial Heatmaps**:
   - Canvas-based 2D grid overlay showing movement corridors, hazard trigger areas, and knockout coordinates.
2. **Party Performance Infographics**:
   - Damage dealt vs damage taken distribution bar charts.
   - MVP turn awards and milestone achievement badge cards.
3. **Living Chronicle Scrubber**:
   - Timeline slider synchronizing turn-by-turn event logs with map position snapshots.
4. **Storybook Verification & Manifest**:
   - Storybook stories for victory, total party kill (TPK), and milestone celebration states.
   - Vendored manifest in `services/campaign_analytics/ui/`.
5. **Frontdoor Blackbox Verification**:
   - Automated blackbox tests verifying analytics API queries and UI manifest exposition.
