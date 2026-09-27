---
id: '0194'
title: Combat Heatmap Canvas Rendering and Subviews Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0052
- TASK-0110
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
target_release: 0.7.0
---

# TASK-0194: Combat Heatmap Canvas Rendering and Subviews Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/campaign_analytics/ui/src/runefoble-combat-heatmap.ts` (334 lines, 66.8% of limit) into modular sub-modules under `services/campaign_analytics/ui/src/heatmap/` (`canvas-renderer.ts`, `heatmap-controls.template.ts`, and `cell-inspector.template.ts`), keeping each sub-module strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/campaign_analytics/ui/src/runefoble-combat-heatmap.ts` contains 334 lines coupling HTML5 2D Canvas rendering routines (color gradients, alpha blending, knockout markers, movement corridor bezier paths), Lit event dispatching, metric filter buttons, and cell detail inspectors in a single component file. As combat telemetry evolves to track spell radius hotspots, this file will exceed 400 lines unless decoupled into focused presentation and rendering utilities.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Visualizer & Lit Component Architecture**: Clean separation between stateful Lit controllers and rendering delegates.
- **ADR-0007: Domain-Driven Design Architecture**: Isolation of campaign analytics presentation layer within `campaign_analytics`.
- **ADR-0012: Theming Tokens & Bauhaus Design System**: Adherence to Bauhaus palette and color contrast tokens for data visualizations.
- **ADR-0013: Microfrontend Bounded Context Architecture**: UI encapsulation within `services/campaign_analytics/ui/`.

## Scope of Work
1. **Modular Rendering Utilities (`services/campaign_analytics/ui/src/heatmap/`)**:
   - `canvas-renderer.ts`: Pure canvas drawing functions for grid lines, heat intensity cells, hazard overlays, movement corridors, and knockout glyphs (< 120 lines).
   - `heatmap-controls.template.ts`: Filter buttons for metric switching (all, damage, hit, movement), legend scales, and summary statistics (< 90 lines).
   - `cell-inspector.template.ts`: Selected/hovered cell detail card, damage breakdown, and casualty listings (< 80 lines).
2. **Component Controller Refactoring (`services/campaign_analytics/ui/src/runefoble-combat-heatmap.ts`)**:
   - Streamline component class to manage `@property` declarations, canvas resize observers, and delegating render calls to modular helpers (< 110 lines).
3. **Verification**:
   - Verify Storybook stories for `<runefoble-combat-heatmap>` render accurately with interactive metric filtering.
   - Run `tests/test_blackbox_campaign_analytics_ui.py` to confirm zero regressions.

## Definition of Done
- `runefoble-combat-heatmap.ts` reduced to < 120 lines.
- All new files in `services/campaign_analytics/ui/src/heatmap/` strictly < 130 lines.
- Storybook stories render without errors or warnings.
- UI blackbox tests pass via `uv run pytest`.
