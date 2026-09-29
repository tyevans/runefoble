---
id: '0363'
title: Character Sheet and Inventory Mutations Playwright BDD Test Suite
status: Refined
created: 2026-09-28
dependencies:
- TASK-0356
- TASK-0357
- TASK-0359
governing_adrs:
- ADR-0002
- ADR-0004
- ADR-0007
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0004
- PRD-0023
governing_stories:
- US-0004
- US-0007
- US-0066
target_release: 0.9.0
---

# TASK-0363: Character Sheet and Inventory Mutations Playwright BDD Test Suite

## Status
Refined

## Summary
Implement an end-to-end Playwright BDD test suite (`e2e/features/character_sheet.feature`) validating character creation, builder modal inputs, sheet inspection, HP delta adjustments, inventory/equipment operations, spell preparation/casting, stand-in guardrails saving, and state persistence across page navigation and reloads per ADR-0014.

## Problem Statement
The Character Sheet microfrontend previously operated in an ephemeral state where equipment toggles, item additions, condition badges, and spell expenditures dispatched custom events that were dropped by the App Shell. Without automated end-to-end browser tests verifying that UI mutations persist through to the backend aggregate (or fallback cache) across browser refreshes, regressions in inventory or health tracking could silently re-emerge.

We must implement automated Playwright BDD scenarios executing real character management user journeys strictly through public frontdoor UI interactions.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Character equipment slots, encumbrance, and conditions.
  - `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md`: Stand-in guardrails and zero-HP stabilization.
- **Governing Architecture & ADRs**:
  - **ADR-0002: Event Sourcing and CQRS with eventsource-py**: Domain state changes via events.
  - **ADR-0004: Lit Web Components and Storybook UI**: Web component presentation.
  - **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend boundaries.
  - **ADR-0014: Behavior-Driven Development (BDD) with Gherkin User Stories and Playwright End-to-End Validation**: BDD testing framework.

## Scope of Work & Implementation Plan
1. **Gherkin Feature Specification (`e2e/features/character_sheet.feature`)**:
   - **Scenario 1: Building and Inspecting a Character**:
     - `Given an authenticated player "Marcus"`
     - `When Marcus opens the character roster and clicks "+ Create Character"`
     - `And fills in name "Thorne Ironbreaker", class "Fighter", and level 4`
     - `Then a new character card appears in the roster`
     - `When Marcus clicks "Inspect Sheet"`
     - `Then the browser navigates to "#/characters/:id" displaying "Thorne Ironbreaker"`.
   - **Scenario 2: Mutating Hit Points and Verifying Persistence**:
     - `When Marcus clicks the "-5 HP" adjustment button`
     - `Then current HP updates from 38 to 33 and health bar recalculates`
     - `When Marcus refreshes the browser page`
     - `Then current HP remains 33`.
   - **Scenario 3: Equipping and Unequipping Gear**:
     - `When Marcus clicks "Equip" on "Longsword +1" in his inventory table`
     - `Then "Longsword +1" appears in the Main Hand equipment slot`
     - `And inventory encumbrance updates`
     - `When Marcus clicks "Unequip"`
     - `Then the Main Hand slot becomes empty`.
   - **Scenario 4: Saving Stand-in Guardrails**:
     - `When Marcus sets the stand-in risk threshold to "cautious" and checks "Avoid Melee"`
     - `And clicks "Save Guardrails"`
     - `Then a toast "Tactical Guardrails Saved!" appears`
     - `And reloading the page retains the "cautious" stance`.
2. **Step Definitions Implementation (`e2e/steps/character_sheet_steps.ts`)**:
   - Pierce shadow DOM on `<runefoble-character-roster>`, `<runefoble-character-builder-modal>`, `<runefoble-character-sheet>`, and `<runefoble-stand-in-guardrails>`.
   - Verify page reload persistence using `page.reload()`.
3. **Execution & CI Integration**:
   - Ensure suite runs cleanly in under 20 seconds.

## INVEST Criteria Evaluation
- **Independent (I)**: Focuses exclusively on character creation, sheet inspection, and mutation persistence.
- **Negotiable (N)**: Item names and stat delta amounts can be adjusted.
- **Valuable (V)**: Guarantees players never lose inventory items, health adjustments, or tactical guardrail settings.
- **Estimable (E)**: Known DOM selectors and REST mutation routes.
- **Small (S)**: Feature file and TypeScript step definitions (< 250 lines).
- **Testable (T)**: Tested with Playwright UI actions and page reload assertions.

## Definition of Done
1. `e2e/features/character_sheet.feature` passes with 100% assertions across supported browsers.
2. HP deltas, equipment changes, and stand-in guardrails persist across `page.reload()`.
3. Zero backdoor database calls; all interactions occur through browser clicks and public APIs.
4. All source files conform to Hard Invariant 6 (<500 lines).
