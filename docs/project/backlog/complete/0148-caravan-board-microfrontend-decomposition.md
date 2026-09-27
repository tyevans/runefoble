---
id: 0148
title: Caravan Board Microfrontend Styles and Component Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0136
- TASK-0147
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0007
- PRD-0018
governing_stories:
- US-0058
target_release: 0.5.0
pr_url: https://github.com/tyevans/runefoble/pull/175
---
# TASK-0148: Caravan Board Microfrontend Styles and Component Decomposition

## Status
Refined

## Summary
Decompose `services/game_session/ui/src/runefoble-caravan-board.ts` (398 lines, 79.6% of limit) and `runefoble-caravan-board.styles.ts` (397 lines, 79.4% of limit) into modular sub-components and style files under `services/game_session/ui/src/caravan/` (`contract_card.ts`, `dispatch_modal.ts`, `board_filters.ts`), keeping all UI files < 150 lines per Hard Invariant 6.

## Problem Statement
Both the component logic and CSS styles of `runefoble-caravan-board` are approaching 400 lines. As new filter controls for hazard risks and cross-campaign reputation tags are introduced, decomposing them into atomic custom elements prevents future invariant breaches while preserving Shadow DOM encapsulation.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Atomic custom element composition and Storybook coverage.
- **ADR-0012: Theming System and Accessibility Contrast Invariants**: Bauhaus token isolation and contrast verification.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Component vendored strictly inside `services/game_session/ui/`.

## Product & User Story References
- **Product Requirement**: [`prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md`](../../product/accepted/prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md)
- **User Story**: [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)

## Detailed Specification & Implementation Plan
1. **Contract Card Sub-Component (`services/game_session/ui/src/caravan/contract_card.ts`)**:
   - Extract individual notice board contract card rendering, reward badges, and status pills (< 120 lines).
2. **Dispatch Modal Sub-Component (`services/game_session/ui/src/caravan/dispatch_modal.ts`)**:
   - Extract escort party assignment and caravan dispatch modal dialog (< 130 lines).
3. **Filter Bar Sub-Component (`services/game_session/ui/src/caravan/board_filters.ts`)**:
   - Extract search input, risk level dropdown, and cargo type filters (< 110 lines).
4. **Styles Decomposition (`services/game_session/ui/src/caravan/styles/`)**:
   - Split styling into `layout.styles.ts`, `card.styles.ts`, and `modal.styles.ts` (< 110 lines each).
5. **Caravan Board Orchestrator (`services/game_session/ui/src/runefoble-caravan-board.ts`)**:
   - Reduce root element to container orchestrating state and sub-components (< 140 lines).
6. **Storybook Stories & Manifest**:
   - Update `runefoble-caravan-board.stories.ts` to showcase modular sub-states; maintain `/ui/manifest` export.

## INVEST Criteria Evaluation
- **Independent (I)**: Frontend refactoring with zero change to external HTTP routes or event schemas.
- **Negotiable (N)**: Sub-component boundaries can adjust as long as all files stay < 180 lines.
- **Valuable (V)**: Protects against file size invariant violations and increases component testability.
- **Estimable (E)**: Standard Lit component extraction and CSS modularization.
- **Small (S)**: Bounded to `services/game_session/ui/src/caravan/`; all files < 150 lines.
- **Testable (T)**: Validated by Storybook story rendering and existing UI blackbox test suites.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular UI Architecture**:
   - `services/game_session/ui/src/caravan/` created with atomic sub-components and modular styles.
   - All source and style files strictly < 180 lines.
2. **Storybook & Frontdoor Test Verification**:
   - Interactive Storybook stories render without console errors.
   - `uv run pytest tests/test_blackbox_caravan_contracts/` and `pnpm run build` pass with zero regressions.
3. **Quality Gates**:
   - Passes `uv run ruff check .` and frontend build verification.
