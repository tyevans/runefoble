---
id: 0158
title: Reactive Combat Reactions & Interrupt Prompt Microfrontend
status: Complete
created: 2026-09-26
dependencies:
- TASK-0155
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0001
governing_stories:
- US-0023
target_release: 0.6.0
pr_url: https://github.com/tyevans/runefoble/pull/179
---
# TASK-0158: Reactive Combat Reactions & Interrupt Prompt Microfrontend

## Status
Refined

## Summary
Build `<runefoble-combat-reaction-prompt>` Web Component in `services/game_session/ui/src/` to display interactive reaction interrupt prompts, ready-action confirmation toasts, and countdown resolution bars during paused combat turns.

## Problem Statement
When combat is paused by a spoken reaction (TASK-0155) or when a ready-action trigger fires, players need immediate, tactile UI prompts to select reaction options ("Cast Shield [-1 slot]", "Opportunity Attack", "Decline") before turn timeout expires.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated Lit Web Component with Shadow DOM.
- **ADR-0012: Theming System and Accessibility Contrast Invariants**: Accessible countdown timers, high-contrast action buttons, and keyboard navigation.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Vendored strictly inside `services/game_session/ui/` and served via `/ui/manifest`.

## Product & User Story References
- **Product Requirement**: [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- **User Story**: [`us-0023-spoken-reaction-interrupts-and-ready-actions.md`](../../user_stories/accepted/us-0023-spoken-reaction-interrupts-and-ready-actions.md)

## Detailed Specification & Implementation Plan
1. **Reaction Prompt Modal Component (`services/game_session/ui/src/runefoble-combat-reaction-prompt.ts`)**:
   - Urgent modal overlay displaying triggered condition, eligible reactions, and time-remaining countdown bar (< 150 lines).
2. **Ready-Action Card (`services/game_session/ui/src/runefoble-ready-action-card.ts`)**:
   - UI panel for configuring trigger phrases and assigning reaction spells/actions (< 130 lines).
3. **Component Styles (`services/game_session/ui/src/runefoble-combat-reaction-prompt.styles.ts`)**:
   - CSS tokens conforming to Bauhaus design system and ADR-0012 contrast guidelines (< 120 lines).
4. **Storybook Stories (`services/game_session/ui/src/runefoble-combat-reaction-prompt.stories.ts`)**:
   - Interactive stories demonstrating countdown state, trigger accepted state, and timeout expired state (< 140 lines).
5. **Manifest & Custom Element Registration**:
   - Register custom element `<runefoble-combat-reaction-prompt>` in `services/game_session/ui/src/index.ts` and verify `/ui/manifest` export.

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes existing reaction REST and WebSocket endpoints from TASK-0155 without modifying server state machines.
- **Negotiable (N)**: Layout and countdown animations can be styled to match theme tokens.
- **Valuable (V)**: Delivers tactile, sub-second reaction UX to the player interface.
- **Estimable (E)**: Standard Lit Web Component with timer state and event emission.
- **Small (S)**: Bounded strictly to `services/game_session/ui/src/`; all files < 160 lines.
- **Testable (T)**: Storybook stories verify visual rendering and blackbox tests verify `/ui/manifest` delivery.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Architecture**:
   - Built and vendored inside `services/game_session/ui/`.
   - All TypeScript and CSS files strictly < 160 lines per Hard Invariant 6.
2. **Storybook Verification**:
   - Interactive stories render cleanly in Storybook with zero console errors.
3. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_reaction_prompt_ui/` asserts `/ui/manifest` export and custom element script bundles.
4. **Quality Gates**:
   - Passes `pnpm run build`, `uv run ruff check .`, and `uv run ruff format --check .`.
