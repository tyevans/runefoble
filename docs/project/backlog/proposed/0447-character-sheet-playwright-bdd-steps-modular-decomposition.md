---
id: '0447'
title: Character Sheet Playwright BDD Steps Modular Decomposition
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0363
governing_adrs:
- ADR-0004
- ADR-0010
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0006
- PRD-0023
governing_stories:
- US-0015
- US-0051
- US-0064
- US-0069
target_release: 0.9.0
---

# TASK-0447: Character Sheet Playwright BDD Steps Modular Decomposition

## Status
Proposed

## Summary
Decompose `e2e/steps/character_sheet_steps.ts` (386 lines, 77.2% of limit) into modular step definition files under `e2e/steps/character_sheet/` (`builder_steps.ts`, `inventory_steps.ts`, `guardrails_steps.ts`, `common.ts`), ensuring all step definition modules remain strictly < 130 lines per Hard Invariant 6 and ADR-0013.

## Problem Statement
`e2e/steps/character_sheet_steps.ts` implements blackbox Playwright BDD frontdoor interactions across character creation modal forms, stats and trait inputs, HP adjustments and condition badges, equipment slot assignments, inventory encumbrance indicators, absentee stand-in tactical guardrails, and page reload state persistence in a single 386-line file. As weapon proficiencies, spell slot tracking, and resting mechanics add additional steps to the BDD suite, this file will rapidly approach and exceed the 500-line invariant limit unless decomposed into focused submodules.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Custom element shadow-piercing locators and event dispatches.
- **ADR-0010: Continuous Integration Pipeline**: Rapid test runs using Playwright BDD test runner.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 130 lines).
- **ADR-0014: Behavior-Driven Development (BDD) with Playwright and Cucumber**: Frontdoor BDD scenario step definitions.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)
  - [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
  - [`us-0015-dynamic-equipment-slots-and-encumbrance.md`](../../user_stories/accepted/us-0015-dynamic-equipment-slots-and-encumbrance.md)
  - [`us-0051-character-sheet-inventory-equipment-and-conditions.md`](../../user_stories/accepted/us-0051-character-sheet-inventory-equipment-and-conditions.md)
  - [`us-0064-character-roster-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-and-party-assignment.md)
  - [`us-0069-deep-linkable-character-sheet-route.md`](../../user_stories/accepted/us-0069-deep-linkable-character-sheet-route.md)

## Scope of Work
1. **Shared Fixtures & Helpers (`e2e/steps/character_sheet/common.ts`)**:
   - Extract `ensureOnCharacterSheet` and common navigation/selector utilities (< 50 lines).
2. **Character Creation & Stats (`e2e/steps/character_sheet/builder_steps.ts`)**:
   - Extract character builder modal steps, name/class/level inputs, and sheet navigation assertions (< 90 lines).
3. **Inventory & Equipment Steps (`e2e/steps/character_sheet/inventory_steps.ts`)**:
   - Extract equipment slot assignments, inventory additions/removals, encumbrance badges, and condition toggles (< 110 lines).
4. **Stand-In Guardrails & Persistence Steps (`e2e/steps/character_sheet/guardrails_steps.ts`)**:
   - Extract absentee stand-in posture directives, zero-HP stabilization triggers, and page reload verification (< 100 lines).
5. **Step Aggregator (`e2e/steps/character_sheet_steps.ts`)**:
   - Re-export submodules or maintain clean index delegation to prevent breaking Cucumber step registry (< 30 lines).
6. **Verification**:
   - Run `npx bddgen && pnpm test:e2e:character-sheet` (or Playwright BDD runner) asserting 100% passing scenarios.

## Definition of Done
1. `e2e/steps/character_sheet_steps.ts` decomposed into `e2e/steps/character_sheet/` submodules strictly < 130 lines each.
2. All 4 character sheet BDD feature scenarios pass with 100% assertions.
3. Code passes `pnpm lint` or equivalent TypeScript typechecks.
