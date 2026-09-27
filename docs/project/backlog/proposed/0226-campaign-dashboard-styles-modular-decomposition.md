---
id: '0226'
title: Campaign Dashboard Styles Modular Decomposition
status: Proposed
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
Proposed

## Summary
Decompose `services/game_session/ui/src/campaigns/runefoble-campaign-dashboard.styles.ts` (314 lines, 62.8% of limit) into modular CSS chunks under `services/game_session/ui/src/campaigns/styles/dashboard/` (`base.styles.ts`, `cards.styles.ts`, `modal.styles.ts`), ensuring all style modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/campaigns/runefoble-campaign-dashboard.styles.ts` contains styling for campaign grid cards, new campaign creation modal dialogs, status badges, empty states, and layout containers. As campaign tagging, archiving, and cover art styling are added, this file will approach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Modular Lit CSS tagged template composition.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Bauhaus geometric tokens and high-contrast color invariants.
- **ADR-0013: Modular Microfrontend Decomposition**: Component subviews strictly < 150 lines.

## Scope of Work
1. **Style Module Decomposition (`services/game_session/ui/src/campaigns/styles/dashboard/`)**:
   - `base.styles.ts`: Host container, header actions, grid layouts, and empty state illustrations (< 110 lines).
   - `cards.styles.ts`: Campaign cards, metadata badges, member count pills, and hover states (< 110 lines).
   - `modal.styles.ts`: Campaign creation modal dialog, inputs, validation warnings, and buttons (< 120 lines).
2. **Aggregator Export (`runefoble-campaign-dashboard.styles.ts`)**:
   - Re-export `campaignDashboardStyles = [baseStyles, cardStyles, modalStyles]` (< 30 lines).
3. **Verification**:
   - Verify Storybook stories render without styling regressions and tests pass.

## Definition of Done
- `runefoble-campaign-dashboard.styles.ts` reduced to < 40 lines.
- Extracted style modules strictly < 130 lines each.
- Storybook stories render with zero visual regressions.
- Passes all formatting and linting checks.
