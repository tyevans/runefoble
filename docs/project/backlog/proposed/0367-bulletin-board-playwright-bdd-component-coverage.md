---
id: '0367'
title: Settlement Bulletin Board Playwright BDD Component Coverage
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0359
governing_adrs:
- ADR-0004
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0025
governing_stories:
- US-0070
target_release: 0.9.0
---

# TASK-0367: Settlement Bulletin Board Playwright BDD Component Coverage

## Status
Proposed

## Summary
Implement a frontdoor-driven Playwright BDD component test suite (`e2e/features/components/bulletin_board.feature`) validating the `<runefoble-bulletin-board>` component across its Storybook story states and public DOM/event behaviors per ADR-0014.

## Problem Statement
The Settlement Bulletin Board component (`frontend/src/components/runefoble-bulletin-board.ts`) provides critical interactive UI capabilities within its bounded context. While exercised in Storybook isolation (`frontend/src/stories/runefoble-bulletin-board.stories.ts`), it lacks automated end-to-end browser BDD tests executing across Shadow DOM boundaries to guarantee that user interactions, event dispatches, property bindings, and Bauhaus theme modes function reliably without regressions.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Component Architecture with Lit, Vite, and Storybook**: Lit Web Components and Shadow DOM encapsulation.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Component boundary isolation and contract events.
- **ADR-0014: Behavior-Driven Development (BDD) with Gherkin User Stories and Playwright End-to-End Validation**: Frontdoor browser BDD testing framework.

## Scope of Work & Implementation Plan
1. **Gherkin Feature Specification (`e2e/features/components/bulletin_board.feature`)**:
   - Scenario: Rendering default component state and initial properties.
   - Scenario: Simulating realistic user interactions (clicks, inputs, hotkeys) via shadow-piercing locators.
   - Scenario: Verifying public CustomEvent emissions and state transitions without internal backdoors.
   - Scenario: Validating Bauhaus design token contrast and theme switching behavior.
2. **Step Definitions Implementation (`e2e/steps/components/bulletin_board_steps.ts`)**:
   - Implement shadow-piercing Playwright locators targeting `<runefoble-bulletin-board>`.
   - Assert observable DOM changes, accessibility attributes, and visual feedback.
3. **Cross-Browser & Quality Gate Verification**:
   - Execute test suite across Chromium, Firefox, and WebKit headless browsers.

## INVEST Criteria Evaluation
- **Independent (I)**: Focuses exclusively on `<runefoble-bulletin-board>` component behaviors and Storybook states.
- **Negotiable (N)**: Step definition naming and specific scenario parameters can be tuned.
- **Valuable (V)**: Protects against silent frontend UI regressions, broken Shadow DOM bindings, or unhandled events.
- **Estimable (E)**: Directly mirrors established Storybook stories and Lit component API contracts.
- **Small (S)**: Scope strictly isolated to a single component test suite (< 150 lines per test file).
- **Testable (T)**: Executable via `make test-e2e` or component test runner with deterministic pass/fail criteria.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Gherkin feature file `e2e/features/components/bulletin_board.feature` authored with frontdoor-only scenarios.
2. Step definitions `e2e/steps/components/bulletin_board_steps.ts` implemented using shadow-piercing locators.
3. 100% of scenarios pass across Chromium, Firefox, and WebKit without backdoor manipulation.
4. All test and feature files strictly under 500 lines per Hard Invariant 6.
