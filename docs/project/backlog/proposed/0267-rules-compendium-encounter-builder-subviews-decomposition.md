---
id: '0267'
title: Rules Compendium Encounter Builder Subviews Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0108
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0008
governing_stories:
- US-0052
target_release: 0.8.0
---

# TASK-0267: Rules Compendium Encounter Builder Subviews Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/rules_compendium/ui/src/runefoble-encounter-builder.ts` (304 lines) into modular subcomponents and helper modules (`encounter-thresholds.ts`, `encounter-roster-view.ts`, `encounter-difficulty-meter.ts`), keeping all source modules strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`runefoble-encounter-builder.ts` contains party XP threshold calculation tables, active monster roster management, difficulty meter gauge rendering, and API synchronization within a single Lit component. As dynamic homebrew rules and multi-party CR calculators are added, this component will exceed 500 lines unless broken down into composable Lit templates and pure helper functions.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Shadow DOM modular subcomponents.
- **ADR-0007: Domain-Driven Design Architecture**: Encapsulation of rules compendium UI logic.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast meters and typography.
- **ADR-0013: Modular Microfrontend Decomposition**: Component modularity and single responsibility.

## Scope of Work
1. **XP Threshold Calculator Helper (`services/rules_compendium/ui/src/encounter-thresholds.ts`)**:
   - Extract `XP_THRESHOLDS_PER_LEVEL` mapping and party threshold computation (< 70 lines).
2. **Difficulty Meter Template (`services/rules_compendium/ui/src/encounter-difficulty-meter.ts`)**:
   - Extract difficulty badge rendering, XP bar percentage calculation, and multiplier display (< 80 lines).
3. **Monster Roster View Template (`services/rules_compendium/ui/src/encounter-roster-view.ts`)**:
   - Extract monster count increment/decrement controls, CR badge rendering, and removal handlers (< 90 lines).
4. **Main Component Orchestrator (`services/rules_compendium/ui/src/runefoble-encounter-builder.ts`)**:
   - Keep top-level state management, event dispatch, and layout assembly (< 120 lines).
5. **Verification**:
   - Verify Storybook stories and existing blackbox tests (`tests/test_rules_compendium_ui.py`) continue to pass.

## Definition of Done
- `runefoble-encounter-builder.ts` decomposed into helper and template modules strictly < 130 lines.
- Storybook component renders correctly across dark, light, and high-contrast modes.
- All tests pass via `uv run pytest tests/test_blackbox_rules_compendium*.py`.
