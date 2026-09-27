---
id: '0199'
title: Campfire Crafting Subviews Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0100
- TASK-0153
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0014
governing_stories:
- US-0044
target_release: 0.7.0
---

# TASK-0199: Campfire Crafting Subviews Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/ui/src/runefoble-campfire-crafting.ts` (323 lines, 64.6% of limit) into modular presentation subviews under `services/game_session/ui/src/campfire/` (`crafting-bench.template.ts`, `boons-display.template.ts`, and `stronghold-status.template.ts`), keeping each module strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/runefoble-campfire-crafting.ts` spans 323 lines implementing reagent selection logic, catalyst dropdowns, risk percentage calculations, campfire storytelling prompts, active boons, and stronghold facility status boards. As new downtime activities and recipes are introduced, this presentation component will cross the 400-line warning threshold unless modularized into focused template modules.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Visualizer & Lit Component Architecture**: Separation of presentation rendering templates from component state controllers.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for downtime crafting and base camp activities.
- **ADR-0012: Theming Tokens & Bauhaus Design System**: Bauhaus design token integration for tactile crafting UI.
- **ADR-0013: Microfrontend Bounded Context Architecture**: UI encapsulation within `services/game_session/ui/`.

## Scope of Work
1. **Modular Subview Templates (`services/game_session/ui/src/campfire/`)**:
   - `crafting-bench.template.ts`: Reagent picker pills, catalyst selector, brewing trigger, risk meter, and outcome notification (< 110 lines).
   - `boons-display.template.ts`: Storytelling campfire prompt card and active resting party boons list (< 90 lines).
   - `stronghold-status.template.ts`: Stronghold facilities upgrade cards, levels, and unlocked workshop bonuses (< 90 lines).
2. **Component Controller Refactoring (`services/game_session/ui/src/runefoble-campfire-crafting.ts`)**:
   - Maintain state management, event dispatching, and risk calculation while importing template functions (< 100 lines).
3. **Verification**:
   - Verify Storybook stories for `<runefoble-campfire-crafting>` render without visual or functional regressions.
   - Run blackbox tests in `tests/test_blackbox_campfire_crafting.py`.

## Definition of Done
- `runefoble-campfire-crafting.ts` reduced to < 110 lines.
- Sub-modules in `services/game_session/ui/src/campfire/` strictly < 120 lines each.
- Storybook stories render cleanly without errors.
- All blackbox tests pass via `uv run pytest tests/test_blackbox_campfire_crafting.py`.
