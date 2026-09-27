---
id: '0223'
title: Session Lobby Styles Modular Decomposition
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
pr_url: https://github.com/tyevans/runefoble/pull/231
---
# TASK-0223: Session Lobby Styles Modular Decomposition

## Status
Refined

## Summary
Decompose `services/game_session/ui/src/lobby/runefoble-session-lobby.styles.ts` (392 lines, 78.4% of limit) into modular CSS modules under `services/game_session/ui/src/lobby/styles/` (`base.styles.ts`, `roster.styles.ts`, `controls.styles.ts`), ensuring all style modules remain strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/lobby/runefoble-session-lobby.styles.ts` has reached 392 lines, bundling container layout, header elements, launch controls, readiness badges, participant cards, character assignment slots, and presence indicators in a single monolithic file. As session pre-flight checks, latency indicators, and voice room previews are added, this file will quickly breach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Modular CSS composition with Lit `css` tagged templates.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Bauhaus design token usage and high-contrast styling invariants.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Component subviews strictly < 150 lines per module.

## Detailed Specification & Implementation Plan
1. **Style Module Decomposition (`services/game_session/ui/src/lobby/styles/`)**:
   - `base.styles.ts`: Host container, flex layouts, header typography, and DM launch controls (< 130 lines).
   - `roster.styles.ts`: Participant cards, avatar wrappers, presence status indicators, and character assignment thumbnails (< 140 lines).
   - `controls.styles.ts`: Readiness toggle buttons, absentee stand-in toggles, and status badges (< 120 lines).
2. **Aggregator Export (`runefoble-session-lobby.styles.ts`)**:
   - Compose the modular styles into `sessionLobbyStyles = [baseStyles, rosterStyles, controlsStyles]` (< 40 lines).
3. **Verification**:
   - Verify all Storybook stories in `services/game_session/ui/src/lobby/` render identically.
   - Run Storybook test suites to verify zero visual or structural regressions.

## INVEST Criteria Evaluation
- **Independent (I)**: Pure CSS refactoring with zero DOM tree changes or component logic alteration.
- **Negotiable (N)**: Style chunk organization can be split cleanly between container layout, roster cards, and button controls.
- **Valuable (V)**: Safeguards against Hard Invariant 6 (500 lines) and improves modularity of session lobby UI.
- **Estimable (E)**: Deterministic extraction of Lit CSS tagged templates into separate modules.
- **Small (S)**: Bounded strictly to `services/game_session/ui/src/lobby/styles/`; all modules < 150 lines.
- **Testable (T)**: Frontdoor verification via Storybook stories and existing blackbox tests in `tests/test_blackbox_campaign_and_lobby.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `runefoble-session-lobby.styles.ts` reduced to < 50 lines.
   - All extracted style modules under `services/game_session/ui/src/lobby/styles/` strictly < 150 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Storybook stories for `<runefoble-session-lobby>` render and pass tests.
   - `tests/test_blackbox_campaign_and_lobby.py` passes cleanly.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_campaign_and_lobby.py`, `uv run ruff check .`, and `uv run ruff format --check .`.
