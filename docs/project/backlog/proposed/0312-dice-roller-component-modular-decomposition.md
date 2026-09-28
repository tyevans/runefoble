---
id: '0312'
title: Dice Roller Component Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0017
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0001
- PRD-0013
governing_stories:
- US-0043
target_release: 0.8.0
---

# TASK-0312: Dice Roller Component Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/ui/src/runefoble-dice-roller.ts` (288 lines, 57.6% of limit) into modular subcomponents and style files (`runefoble-dice-roller.ts`, `runefoble-dice-roller.styles.ts`, `dice-evaluator.ts`), keeping each file strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/runefoble-dice-roller.ts` encapsulates Lit component templates, Bauhaus geometry rendering, dice physics state, roll history tracking, and dice arithmetic evaluation in a single 288-line file. Decoupling CSS styles and the arithmetic evaluator into dedicated submodules improves maintainability and protects against exceeding the 500-line limit.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Microfrontend Design System**: Design token inheritance and styles isolation.
- **ADR-0012: Dark and Light Mode Color Tokens**: Contrast invariants and token usage.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 150 lines).

## Scope of Work
1. **Dice Roller Styles (`services/game_session/ui/src/runefoble-dice-roller.styles.ts`)**:
   - Extract component CSS styles, keyframes, and Bauhaus token bindings (< 90 lines).
2. **Dice Arithmetic & Evaluator (`services/game_session/ui/src/dice-evaluator.ts`)**:
   - Extract dice notation parser and arithmetic evaluator functions (< 80 lines).
3. **Component View (`services/game_session/ui/src/runefoble-dice-roller.ts`)**:
   - Retain Lit component class, reactive properties, and template rendering importing external styles and evaluator (< 120 lines).
4. **Verification**:
   - Run `pnpm test` or Storybook validation to confirm identical visual and behavioral output.

## Definition of Done
- `runefoble-dice-roller.styles.ts` and `dice-evaluator.ts` extracted.
- `services/game_session/ui/src/runefoble-dice-roller.ts` reduced to < 150 lines.
- All Storybook stories and unit tests continue passing without regression.
