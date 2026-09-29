---
id: '0344'
title: Campaign Dashboard Component Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0209
- TASK-0226
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0067
target_release: 0.8.0
---

# TASK-0344: Campaign Dashboard Component Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/ui/src/campaigns/runefoble-campaign-dashboard.ts` (280 lines, 56.0% of limit) into modular subviews and controllers under `services/game_session/ui/src/campaigns/dashboard/` (`filter-bar.ts`, `campaign-grid.ts`, `campaign-card.ts`), with an aggregator component at `services/game_session/ui/src/campaigns/runefoble-campaign-dashboard.ts`, ensuring all submodules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/campaigns/runefoble-campaign-dashboard.ts` bundles search input filtering, role filter buttons (all, dming, playing), empty states, campaign grid card rendering, modal visibility toggles, and event dispatching in a single Lit element. As multi-campaign tags, favorite bookmarks, and campaign archive filters are introduced, this component will exceed 400 lines unless modularized into focused template sub-components.

## Governing Architecture & ADRs
- **ADR-0004: Lit Microfrontends with Shadow DOM Encapsulation**: Pure presentation web components.
- **ADR-0012: CSS Custom Properties and Bauhaus Design Tokens**: Standard design tokens and contrast compliance.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Keep individual component files < 110 lines.

## Scope of Work
1. **Filter & Search Controls (`services/game_session/ui/src/campaigns/dashboard/filter-bar.ts`)**:
   - Extract search bar, role filter tabs, and sort dropdown templates (< 80 lines).
2. **Campaign Card Element (`services/game_session/ui/src/campaigns/dashboard/campaign-card.ts`)**:
   - Extract individual campaign card template, status badges, setting icon, and click handlers (< 90 lines).
3. **Campaign Grid View (`services/game_session/ui/src/campaigns/dashboard/campaign-grid.ts`)**:
   - Extract grid container, empty state illustrations, and loading placeholders (< 75 lines).
4. **Main Dashboard Container (`services/game_session/ui/src/campaigns/runefoble-campaign-dashboard.ts`)**:
   - Refactor into a clean controller composing the subviews (< 95 lines).
5. **Verification**:
   - Ensure Storybook stories and unit tests in `frontend/test/` pass without regressions.

## Definition of Done
- `services/game_session/ui/src/campaigns/dashboard/` subviews strictly < 110 lines each per Hard Invariant 6.
- Main `runefoble-campaign-dashboard.ts` reduced to < 100 lines.
- Storybook stories for `<runefoble-campaign-dashboard>` render correctly.
- Passes all frontend tests via `npm run test` in `frontend/`.
