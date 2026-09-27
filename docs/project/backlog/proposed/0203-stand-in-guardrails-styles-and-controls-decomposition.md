---
id: '0203'
title: Stand-In Guardrails Microfrontend Styles and Controls Modular Decomposition
status: Proposed
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
Proposed

## Summary
Decompose `services/character_sheet/ui/src/runefoble-stand-in-guardrails.ts` (312 lines, 62.4% of limit) by extracting inline Bauhaus CSS styles into `services/character_sheet/ui/src/runefoble-stand-in-guardrails.styles.ts` and form control templates into `runefoble-stand-in-guardrails.templates.ts`, keeping all modules strictly < 150 lines per Hard Invariant 6, ADR-0004, and ADR-0013.

## Problem Statement
`services/character_sheet/ui/src/runefoble-stand-in-guardrails.ts` currently embeds 122 lines of Bauhaus CSS styling directly within `static styles = css`...`` alongside component state, ally management, and form rendering. As absent player tactical policies expand in Milestone 9 (such as remote voting triggers, custom reaction conditions, and spell slot preservation rules), this monolithic component will soon breach the 400-line warning threshold unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Design System**: Consistent typography, design tokens, and modular UI structure.
- **ADR-0012: Theming Tokens & Dark/Light Mode Contrast**: Bauhaus geometric styling and CSS token isolation.
- **ADR-0013: Microfrontend Bounded Context Architecture**: UI encapsulation within `services/character_sheet/ui/`.

## Scope of Work
1. **Styles Extraction (`services/character_sheet/ui/src/runefoble-stand-in-guardrails.styles.ts`)**:
   - Move all CSS rules (layout cards, risk toggles, priority lists, status badges) into a dedicated style module (< 120 lines).
2. **Templates Submodule (`services/character_sheet/ui/src/runefoble-stand-in-guardrails.templates.ts`)**:
   - Extract helper renderers for ally protection tags, slider controls, and custom priority chips (< 90 lines).
3. **Component Controller (`services/character_sheet/ui/src/runefoble-stand-in-guardrails.ts`)**:
   - Refactor root `<runefoble-stand-in-guardrails>` element to import external styles and templates (< 120 lines).
4. **Verification**:
   - Verify Storybook stories for `<runefoble-stand-in-guardrails>` render with zero visual regressions.
   - Run blackbox tests in `tests/test_blackbox_stand_in_guardrails.py`.

## Definition of Done
- `runefoble-stand-in-guardrails.ts` reduced to < 130 lines.
- `runefoble-stand-in-guardrails.styles.ts` and `runefoble-stand-in-guardrails.templates.ts` created and strictly < 130 lines each.
- Storybook stories render without errors.
- All workspace tests pass via `uv run pytest`.
