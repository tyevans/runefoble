---
id: '0220'
title: Campaign Members Styles Modular Decomposition
status: Complete
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/229
---
# TASK-0220: Campaign Members Styles Modular Decomposition

## Status
Refined

## Summary
Decompose `services/game_session/ui/src/campaigns/runefoble-campaign-members.styles.ts` (432 lines, 86.4% of limit) into modular CSS modules under `services/game_session/ui/src/campaigns/styles/` (`base.styles.ts`, `roster.styles.ts`, `modal.styles.ts`, `badge.styles.ts`), ensuring all style modules remain strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/campaigns/runefoble-campaign-members.styles.ts` has grown to 432 lines, bundling container layout, header styling, roster cards, Zanzibar role badges, invite modals, remove-member confirmations, and empty states in a single file. As additional role management features and permissions are added, this file will imminently breach the 500-line hard invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Modular CSS composition with Lit `css` tagged templates.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Bauhaus design token usage and high-contrast styling invariants.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Component subviews strictly < 150 lines per module.

## Detailed Specification & Implementation Plan
1. **Style Module Decomposition (`services/game_session/ui/src/campaigns/styles/`)**:
   - `base.styles.ts`: Host container, flex layouts, typography, header, and buttons (< 120 lines).
   - `roster.styles.ts`: Member list, roster cards, avatar badges, and empty states (< 120 lines).
   - `modal.styles.ts`: Invite link modal, remove confirmation dialog, backdrop, and copy buttons (< 130 lines).
   - `badge.styles.ts`: Role selector dropdowns, Zanzibar permission badges, and status pills (< 90 lines).
2. **Aggregator Export (`runefoble-campaign-members.styles.ts`)**:
   - Compose the modular styles into `campaignMembersStyles = [baseStyles, rosterStyles, modalStyles, badgeStyles]` (< 40 lines).
3. **Verification**:
   - Verify all Storybook stories in `services/game_session/ui/src/campaigns/` render identically.
   - Run Storybook test suites to verify zero visual or structural regressions.

## INVEST Criteria Evaluation
- **Independent (I)**: Pure CSS refactoring with zero DOM tree changes or component logic alteration.
- **Negotiable (N)**: Style chunk groupings can be organized by UI section or element responsibility.
- **Valuable (V)**: Safeguards against Hard Invariant 6 (500 lines) and improves modularity of campaign membership UI.
- **Estimable (E)**: Deterministic extraction of Lit CSS tagged templates into separate modules.
- **Small (S)**: Bounded strictly to `services/game_session/ui/src/campaigns/styles/`; all modules < 150 lines.
- **Testable (T)**: Frontdoor verification via Storybook stories and existing blackbox tests in `tests/test_blackbox_campaign_and_lobby.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `runefoble-campaign-members.styles.ts` reduced to < 50 lines.
   - All extracted style modules under `services/game_session/ui/src/campaigns/styles/` strictly < 150 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Storybook stories for `<runefoble-campaign-members>` render and pass tests.
   - `tests/test_blackbox_campaign_and_lobby.py` passes cleanly.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_campaign_and_lobby.py`, `uv run ruff check .`, and `uv run ruff format --check .`.
