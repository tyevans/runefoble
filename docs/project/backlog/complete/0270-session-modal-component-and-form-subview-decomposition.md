---
id: '0270'
title: Session Modal Component and Form Styles Modular Decomposition
status: Complete
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0012
governing_prds: []
governing_stories: []
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/302
---
# TASK-0270: Session Modal Component and Form Styles Modular Decomposition

## Status
Refined

## Summary
Decompose `frontend/src/components/runefoble-session-modal.ts` (387 lines, 77.4% of limit) by extracting inline styles into a dedicated styles module `frontend/src/styles/session-modal.styles.ts` and isolating form field sub-renderers, reducing the main component to < 180 lines.

## Problem Statement
`frontend/src/components/runefoble-session-modal.ts` currently embeds nearly 200 lines of CSS alongside form submission, validation logic, and template rendering. As additional scheduling options (recurring schedules, timezone selectors, and stand-in pre-allocations) are added, this file will rapidly approach the 500-line invariant limit unless styles and form subviews are cleanly decomposed.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/develop-lit-components-in-storybook.md`: Component style separation in Lit and Storybook stories.
  - `docs/reference/design-tokens-and-themes.md`: Bauhaus dialog, form input, and elevation tokens.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Separation of component styles from render templates.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Form control contrast and modal focus trap styling.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
  - [`us-0065-pre-game-assembly-and-session-lobby.md`](../../user_stories/accepted/us-0065-pre-game-assembly-and-session-lobby.md)
  - [`us-0067-unified-campaign-detail-hero-header-and-tabbed-navigation.md`](../../user_stories/accepted/us-0067-unified-campaign-detail-hero-header-and-tabbed-navigation.md)

## Detailed Specification & Implementation Plan
1. **Style Module Extraction (`frontend/src/styles/session-modal.styles.ts`)**:
   - Extract modal backdrop, dialog card, form field groups, radio status selectors, buttons, and error banner styles (< 160 lines).
2. **Component Refactoring (`frontend/src/components/runefoble-session-modal.ts`)**:
   - Import `sessionModalStyles` from `../styles/session-modal.styles.ts`.
   - Keep lifecycle, form state handling, and template rendering focused and clean (< 180 lines).
3. **Verification**:
   - Verify Storybook stories for `<runefoble-session-modal>` pass without visual regression.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal style and template refactoring without changing the component's public interface or events.
- **Negotiable (N)**: CSS grouping names and sub-renderer splits can be tuned.
- **Valuable (V)**: Protects session modal component from breaching the 500-line limit.
- **Estimable (E)**: Straightforward CSS extraction and template pruning.
- **Small (S)**: Target files will each be under 180 lines.
- **Testable (T)**: Existing tests and Storybook stories immediately verify visual and functional parity.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `frontend/src/components/runefoble-session-modal.ts` reduced to < 200 lines.
2. Extracted `frontend/src/styles/session-modal.styles.ts` strictly < 180 lines.
3. Modal opens, schedules sessions, and reports validation errors identically across themes.
4. Code passes lint and typecheck (`pnpm run lint` and `pnpm run build`).
