---
id: '0270'
title: Session Modal Component and Form Styles Modular Decomposition
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

# TASK-0270: Session Modal Component and Form Styles Modular Decomposition

## Status
Proposed

## Summary
Decompose `frontend/src/components/runefoble-session-modal.ts` (387 lines, 77.4% of limit) by extracting inline styles into a dedicated styles module `frontend/src/styles/session-modal.styles.ts` and isolating form field sub-renderers, reducing the main component to < 180 lines.

## Problem Statement
`frontend/src/components/runefoble-session-modal.ts` currently embeds nearly 200 lines of CSS alongside form submission, validation logic, and template rendering. As additional scheduling options (recurring schedules, timezone selectors, and stand-in pre-allocations) are added, this file will rapidly approach the 500-line invariant limit.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Separation of component styles from render templates.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Form control contrast and modal focus trap styling.

## Scope of Work
1. **Style Module Extraction (`frontend/src/styles/session-modal.styles.ts`)**:
   - Extract modal backdrop, dialog card, form field groups, radio status selectors, buttons, and error banner styles (< 160 lines).
2. **Component Refactoring (`frontend/src/components/runefoble-session-modal.ts`)**:
   - Import `sessionModalStyles` from `../styles/session-modal.styles.ts`.
   - Keep lifecycle, form state handling, and template rendering focused and clean (< 180 lines).
3. **Verification**:
   - Verify Storybook stories for `<runefoble-session-modal>` pass without visual regression.

## Definition of Done
- `frontend/src/components/runefoble-session-modal.ts` reduced to < 200 lines.
- Extracted `frontend/src/styles/session-modal.styles.ts` strictly < 180 lines.
- Modal opens, schedules sessions, and reports validation errors identically.
- Code passes lint and typecheck.
