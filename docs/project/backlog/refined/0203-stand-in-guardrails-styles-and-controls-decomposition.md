---
id: '0203'
title: Stand-In Guardrails Microfrontend Styles and Controls Modular Decomposition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0055
- TASK-0112
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0006
- PRD-0019
governing_stories:
- US-0017
- US-0027
- US-0059
target_release: 0.7.0
---

# TASK-0203: Stand-In Guardrails Microfrontend Styles and Controls Modular Decomposition

## Status
Refined

## Summary
Decompose `services/character_sheet/ui/src/runefoble-stand-in-guardrails.ts` (311 lines, 62.2% of limit) by extracting inline Bauhaus CSS styles into `services/character_sheet/ui/src/runefoble-stand-in-guardrails.styles.ts` and form control templates into `runefoble-stand-in-guardrails.templates.ts`, keeping all modules strictly < 140 lines per Hard Invariant 6, ADR-0004, ADR-0012, and ADR-0013.

## Problem Statement
`services/character_sheet/ui/src/runefoble-stand-in-guardrails.ts` currently embeds 122 lines of Bauhaus CSS styling directly within `static styles = css`...`` alongside component state, ally management, and form rendering. As absent player tactical policies expand in Milestone 9 (such as remote voting triggers, custom reaction conditions, and spell slot preservation rules), this monolithic component will soon breach the 400-line warning threshold unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Design System**: Consistent typography, design tokens, and modular UI structure.
- **ADR-0012: Theming Tokens & Dark/Light Mode Contrast**: Bauhaus geometric styling and CSS token isolation.
- **ADR-0013: Microfrontend Bounded Context Architecture**: UI encapsulation within `services/character_sheet/ui/`.

## Detailed Specification & Implementation Plan
1. **Styles Extraction (`services/character_sheet/ui/src/runefoble-stand-in-guardrails.styles.ts`)**:
   - Move all CSS rules (layout cards, risk toggles, priority lists, status badges, Bauhaus geometric accents) into a dedicated style module (< 120 lines).
2. **Templates Submodule (`services/character_sheet/ui/src/runefoble-stand-in-guardrails.templates.ts`)**:
   - Extract helper renderers for ally protection tags, slider controls, posture selectors, and custom priority chips (< 100 lines).
3. **Component Controller Refactoring (`services/character_sheet/ui/src/runefoble-stand-in-guardrails.ts`)**:
   - Refactor root `<runefoble-stand-in-guardrails>` element to import external styles and templates, focusing strictly on property state and event dispatching (< 130 lines).
4. **Verification**:
   - Verify Storybook stories for `<runefoble-stand-in-guardrails>` render with zero visual regressions.
   - Run blackbox tests in `tests/test_blackbox_stand_in_guardrails.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Changes strictly localized to `services/character_sheet/ui/src/runefoble-stand-in-guardrails*`.
- **Negotiable (N)**: Style tokens and template abstractions preserve existing HTML tag contracts and attributes.
- **Valuable (V)**: Adheres to ADR-0013 microfrontend best practices and protects against Hard Invariant 6.
- **Estimable (E)**: Standard Lit Web Component style/template extraction pattern used throughout the repo.
- **Small (S)**: Scope strictly isolated to modularizing one Web Component (< 140 lines per module).
- **Testable (T)**: Frontdoor verification via Storybook stories and existing blackbox tests.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `runefoble-stand-in-guardrails.ts` reduced to < 130 lines.
   - `runefoble-stand-in-guardrails.styles.ts` and `runefoble-stand-in-guardrails.templates.ts` created and strictly < 130 lines each.
2. **Frontdoor Verification**:
   - `<runefoble-stand-in-guardrails>` component renders correctly and dispatches policy update events.
   - Storybook stories render without errors.
   - All workspace tests pass via `uv run pytest tests/test_blackbox_stand_in_guardrails.py`.
3. **Quality Gates**:
   - Frontend build passes cleanly.
   - Python code formatted and linted cleanly.
