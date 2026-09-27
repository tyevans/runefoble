---
id: '0220'
title: Campaign Members Styles Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0012
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0220: Campaign Members Styles Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/ui/src/campaigns/runefoble-campaign-members.styles.ts` (433 lines, 86.6% of limit) into modular CSS modules under `services/game_session/ui/src/campaigns/styles/` (`base.styles.ts`, `roster.styles.ts`, `modal.styles.ts`, `badge.styles.ts`), ensuring all style modules remain strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/campaigns/runefoble-campaign-members.styles.ts` has grown to 433 lines, bundling container layout, header styling, roster cards, Zanzibar role badges, invite modals, remove-member confirmations, and empty states in a single file. As additional role management features and permissions are added, this file will imminently breach the 500-line hard invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Modular CSS composition with Lit `css` tagged templates.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Bauhaus design token usage and high-contrast styling invariants.

## Scope of Work
1. **Style Module Decomposition (`services/game_session/ui/src/campaigns/styles/`)**:
   - `base.styles.ts`: Host container, flex layouts, typography, header, and buttons (< 120 lines).
   - `roster.styles.ts`: Member list, roster cards, avatar badges, and empty states (< 120 lines).
   - `modal.styles.ts`: Invite link modal, remove confirmation dialog, backdrop, and copy buttons (< 130 lines).
   - `badge.styles.ts`: Role selector dropdowns, Zanzibar permission badges, and status pills (< 90 lines).
2. **Aggregator Export (`runefoble-campaign-members.styles.ts`)**:
   - Compose the modular styles into `campaignMembersStyles = [baseStyles, rosterStyles, modalStyles, badgeStyles]` (< 40 lines).
3. **Verification**:
   - Verify all Storybook stories in `services/game_session/ui/src/campaigns/` render identically.
   - Run Storybook build and test suites to verify zero visual or structural regressions.

## Definition of Done
- `runefoble-campaign-members.styles.ts` reduced to < 50 lines.
- All extracted style modules under `services/game_session/ui/src/campaigns/styles/` strictly < 150 lines.
- Storybook stories for `<runefoble-campaign-members>` render and pass tests.
- Linting and typechecks pass cleanly (`pnpm run build` / `npm run test` where applicable).
