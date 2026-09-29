---
id: '0288'
title: Frontend Character Management Test Suite Modular Decomposition
status: Refined
created: 2026-09-28
dependencies:
- TASK-0258
governing_adrs:
- ADR-0004
- ADR-0010
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0006
- PRD-0023
governing_stories:
- US-0064
- US-0069
- US-0070
- US-0071
target_release: 0.8.0
---

# TASK-0288: Frontend Character Management Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `frontend/test/character-management-and-profile.test.ts` (331 lines, 66.2% of limit) into modular TypeScript test submodules under `frontend/test/character_management/` (`navigation.test.ts`, `creation.test.ts`, `profile.test.ts`, `invariants.test.ts`), ensuring all test modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`frontend/test/character-management-and-profile.test.ts` handles character creation modal events, character roster inspection routes, staging lobby character selection, dynamic VTT card binding, user profile settings view rendering, and campaign deduplication assertions in a single 331-line suite. As character sheets support multiclassing and advanced equipment interactions, this frontend test suite will approach the 500-line invariant limit unless modularized into focused test suites.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Character inventory, traits, and condition badges.
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: Deep-linkable client routing, breadcrumbs, and title resolvers.
  - `docs/how-to/coordinate-game-session-lobby-and-readiness.md`: Pre-game lobby readiness and character assignments.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Character card custom element encapsulation and test contracts.
  - **ADR-0010: Continuous Integration Pipeline**: Rapid test runs using Node native test runner (`node:test`).
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast character token styling and badges.
  - **ADR-0013: Frontend Microfrontend Architecture**: Decoupled character roster and pre-game lobby components.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)
  - [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
  - [`us-0064-character-roster-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-and-party-assignment.md)
  - [`us-0069-deep-linkable-character-sheet-route.md`](../../user_stories/accepted/us-0069-deep-linkable-character-sheet-route.md)

## Detailed Specification & Implementation Plan
1. **Route Navigation & Dynamic Titles (`frontend/test/character_management/navigation.test.ts`)**:
   - Extract character roster route matching, active view resolution, dynamic document title resolution, and deep linking assertions (< 100 lines).
2. **Character Creation & Data Mutations (`frontend/test/character_management/creation.test.ts`)**:
   - Extract character creation payload validation, campaign filtering, mock persistence, and fallback character state mutations (< 110 lines).
3. **Profile Settings & Campaign Deduplication (`frontend/test/character_management/profile.test.ts`)**:
   - Extract user profile view rendering, auth session claims, campaign creation idempotency, and duplicate submission prevention (< 100 lines).
4. **Bauhaus Theming & Invariants (`frontend/test/character_management/invariants.test.ts`)**:
   - Extract source file line count limits (< 500 lines), Bauhaus design token verification, and custom element encapsulation assertions (< 80 lines).
5. **Verification**:
   - Safely remove monolithic `frontend/test/character-management-and-profile.test.ts` and ensure `pnpm test` / `npm test` runs with 100% passing tests.

## INVEST Criteria Evaluation
- **Independent (I)**: Pure test suite decomposition without affecting UI runtime components.
- **Negotiable (N)**: Submodule file names and fixture sharing can be adapted cleanly.
- **Valuable (V)**: Safeguards frontend character management test suites against breaching the 500-line limit.
- **Estimable (E)**: Existing tests are 100% passing; clean partition into 4 focused test files.
- **Small (S)**: Each extracted test module strictly < 130 lines.
- **Testable (T)**: Directly executable via `pnpm test` in `frontend/`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `frontend/test/character-management-and-profile.test.ts` decomposed into `frontend/test/character_management/` suite.
2. All extracted test modules strictly < 130 lines per Hard Invariant 6.
3. 100% of test assertions pass via `pnpm test` (or `npm test`) in `frontend/`.
4. Monolithic `frontend/test/character-management-and-profile.test.ts` safely removed.
