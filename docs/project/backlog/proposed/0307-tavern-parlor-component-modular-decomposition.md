---
id: '0307'
title: Tavern Parlor Component Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0103
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0014
governing_stories:
- US-0047
target_release: 0.8.0
---

# TASK-0307: Tavern Parlor Component Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/ui/src/runefoble-tavern-parlor.ts` (294 lines, 58.8% of limit) into modular subview templates under `services/game_session/ui/src/tavern/` (`views/dice-tab.ts`, `views/drinking-tab.ts`, `views/merchant-tab.ts`, `types.ts`), keeping each file strictly < 90 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/runefoble-tavern-parlor.ts` encapsulates three distinct minigame experiences (Liar's Dice wagering, drinking contest endurance with DSP voice audio, and merchant haggling interactions) in a single 294-line Lit component. As rich animation cues, sound effects, and multi-player wagering are enhanced, this component will exceed 500 lines unless decoupled into dedicated subview renderers.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Shadow DOM encapsulation and clean component subview composition.
- **ADR-0007: Domain-Driven Design Architecture**: Clean separation of minigame sub-features.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (subviews < 90 lines).

## Scope of Work
1. **Types Submodule (`services/game_session/ui/src/tavern/types.ts`)**:
   - Extract `LiarsDiceBid`, minigame tab enums, and intoxication state definitions (< 40 lines).
2. **Dice Tab View (`services/game_session/ui/src/tavern/views/dice-tab.ts`)**:
   - Extract Liar's Dice cup shaking, bidding controls, and dice hand rendering (< 80 lines).
3. **Drinking Tab View (`services/game_session/ui/src/tavern/views/drinking-tab.ts`)**:
   - Extract drinking contest mug interactions, intoxication meter, and DSP badge renderers (< 70 lines).
4. **Merchant Tab View (`services/game_session/ui/src/tavern/views/merchant-tab.ts`)**:
   - Extract merchant mood score, haggling offer inputs, and voice bark speech bubble (< 80 lines).
5. **Component Coordinator (`services/game_session/ui/src/runefoble-tavern-parlor.ts`)**:
   - Delegate subview rendering to modular template functions (< 90 lines).
6. **Verification**:
   - Run `npm test` in `frontend/` and `uv run pytest tests/test_blackbox_tavern_and_haggling.py`.

## Definition of Done
- `runefoble-tavern-parlor.ts` reduced to < 90 lines, delegating to `tavern/views/` subviews.
- All extracted submodules strictly < 90 lines each per Hard Invariant 6.
- Storybook stories for tavern parlor render and function without regressions.
- Tavern blackbox tests pass cleanly.
