---
id: '0196'
title: Campaign Atlas Layers and Pins Subviews Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0106
- TASK-0135
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0015
governing_stories:
- US-0050
- US-0058
target_release: 0.7.0
---

# TASK-0196: Campaign Atlas Layers and Pins Subviews Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/campaign_lore/ui/src/runefoble-campaign-atlas.ts` (331 lines, 66.2% of limit) into modular subviews under `services/campaign_lore/ui/src/atlas/` (`territory-renderer.template.ts`, `pins-layer.template.ts`, and `codex-sidebar.template.ts`), keeping each subview strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`services/campaign_lore/ui/src/runefoble-campaign-atlas.ts` currently spans 331 lines implementing multi-layer SVG world map rendering, geopolitical territory polygon math, interactive milestone pins, era timeline filtering, and the living party codex drawer. As West Marches persistent frontier settlements and shared havens are introduced, this file will cross the 400-line warning threshold unless modularized into focused presentation sub-components.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Visualizer & Lit Component Architecture**: Separation of presentation templates from component state controllers.
- **ADR-0007: Domain-Driven Design Architecture**: Clean boundaries for campaign worldbuilding and lore exploration.
- **ADR-0012: Theming Tokens & Bauhaus Design System**: Unified design tokens for map overlays and cartographic typography.
- **ADR-0013: Microfrontend Bounded Context Architecture**: UI encapsulation within `services/campaign_lore/ui/`.

## Scope of Work
1. **Modular Subview Templates (`services/campaign_lore/ui/src/atlas/`)**:
   - `territory-renderer.template.ts`: SVG polygon generation for geopolitical borders, contested territory cross-hatching, and faction color fills (< 110 lines).
   - `pins-layer.template.ts`: Milestone pins, era timeline filtering, coordinate markers, and pin placement click handlers (< 100 lines).
   - `codex-sidebar.template.ts`: Slide-out living party codex notes, illuminated parchment typography, and linked entity chips (< 100 lines).
2. **Component Controller Refactoring (`services/campaign_lore/ui/src/runefoble-campaign-atlas.ts`)**:
   - Retain core state (active layer, active era, selected pins, zoom/pan transforms) and delegate rendering to modular templates (< 110 lines).
3. **Verification**:
   - Verify Storybook stories for `<runefoble-campaign-atlas>` render cleanly across layers and eras.
   - Run `tests/test_blackbox_campaign_atlas.py` to ensure all frontdoor behaviors remain green.

## Definition of Done
- `runefoble-campaign-atlas.ts` reduced to < 120 lines.
- Sub-modules in `services/campaign_lore/ui/src/atlas/` strictly < 120 lines each.
- Storybook stories render without errors.
- Blackbox test suite passes via `uv run pytest tests/test_blackbox_campaign_atlas.py`.
