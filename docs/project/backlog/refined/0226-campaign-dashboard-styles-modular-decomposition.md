---
id: '0226'
title: Campaign Dashboard Styles Modular Decomposition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0209
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0063
target_release: 0.8.0
---

# TASK-0226: Campaign Dashboard Styles Modular Decomposition

## Status
Refined

## Summary
Decompose `services/game_session/ui/src/campaigns/runefoble-campaign-dashboard.styles.ts` (314 lines, 62.8% of limit) into modular CSS chunks under `services/game_session/ui/src/campaigns/styles/dashboard/` (`base.styles.ts`, `cards.styles.ts`, `modal.styles.ts`), ensuring all style modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/campaigns/runefoble-campaign-dashboard.styles.ts` contains styling for campaign grid cards, new campaign creation modal dialogs, status badges, empty states, and layout containers. As campaign tagging, archiving, and cover art styling are added, this file will approach the 500-line limit unless decomposed.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit component CSS patterns and Storybook verification.
  - `docs/reference/design-tokens-and-themes.md`: Bauhaus typography, border radii, and color elevation tokens.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Modular Lit CSS tagged template composition.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Bauhaus geometric tokens and high-contrast color invariants.
  - **ADR-0013: Modular Microfrontend Decomposition**: Component subviews strictly < 150 lines.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
  - [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)

## Detailed Specification & Implementation Plan
1. **Style Module Decomposition (`services/game_session/ui/src/campaigns/styles/dashboard/`)**:
   - `base.styles.ts`: Host container, header actions, grid layouts, and empty state illustrations (< 110 lines).
   - `cards.styles.ts`: Campaign cards, metadata badges, member count pills, and hover states (< 110 lines).
   - `modal.styles.ts`: Campaign creation modal dialog, inputs, validation warnings, and buttons (< 120 lines).
2. **Aggregator Export (`runefoble-campaign-dashboard.styles.ts`)**:
   - Re-export `campaignDashboardStyles = [baseStyles, cardStyles, modalStyles]` (< 30 lines).
3. **Verification**:
   - Verify Storybook stories render without styling regressions and tests pass.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal style decomposition without modifying component API or event contracts.
- **Negotiable (N)**: Style sheet chunk boundaries can be adjusted.
- **Valuable (V)**: Protects campaign dashboard styles from breaching the 500-line invariant limit.
- **Estimable (E)**: Straightforward CSS rule partitioning into modular Lit CSS tagged templates.
- **Small (S)**: Target files will each be strictly < 130 lines.
- **Testable (T)**: Storybook visual checks and frontend build verify CSS integrity.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `runefoble-campaign-dashboard.styles.ts` reduced to < 40 lines.
2. Extracted style modules under `styles/dashboard/` strictly < 130 lines each.
3. Storybook stories for `<runefoble-campaign-dashboard>` render with zero visual regressions.
4. Passes `pnpm run lint` and `pnpm run build` in frontend.
