---
id: '0331'
title: Campaign Analytics Component Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0110
- TASK-0320
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
target_release: 0.8.0
---

# TASK-0331: Campaign Analytics Component Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/campaign_analytics/ui/src/runefoble-campaign-analytics.ts` (271 lines, 54.2% of limit) into modular sub-modules under `services/campaign_analytics/ui/src/` (`controllers/campaign-analytics-controller.ts`, `templates/campaign-analytics.template.ts`, and core component `runefoble-campaign-analytics.ts`), keeping all source files strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`services/campaign_analytics/ui/src/runefoble-campaign-analytics.ts` combines remote API telemetry fetching, error handling state, active tab navigation orchestration, and HTML subview rendering (MVP statistics, spatial heatmap embeds, chronicle milestones) in a single monolithic Lit component. Adding enhanced export capabilities or filtering controls will push this component past the 500-line invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Microfrontend Design System**: Design token inheritance and component composition.
- **ADR-0012: Theming System and Contrast Invariants**: Theming and color contrast invariants.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Analytics Data Controller (`services/campaign_analytics/ui/src/controllers/campaign-analytics-controller.ts`)**:
   - Extract API telemetry fetching, session/encounter query parameter assembly, error state management, and tab switching logic (< 95 lines).
2. **HTML Templates Submodule (`services/campaign_analytics/ui/src/templates/campaign-analytics.template.ts`)**:
   - Extract tab button header rendering, MVP performance card view, heatmap tab wrapper, and chronicle timeline subviews (< 100 lines).
3. **Core Component Refactoring (`services/campaign_analytics/ui/src/runefoble-campaign-analytics.ts`)**:
   - Refactor the main Lit element to compose the controller and templates cleanly (< 80 lines).
4. **Verification**:
   - Run frontend tests and Storybook component rendering to ensure zero visual or functional regressions.

## Definition of Done
- `runefoble-campaign-analytics.ts` decomposed into controller and template sub-modules.
- All extracted files strictly < 110 lines each per Hard Invariant 6.
- Frontend test suite and Storybook stories pass without warnings or errors.
