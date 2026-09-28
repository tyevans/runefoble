---
id: '0287'
title: Frontend App Shell Test Suite Modular Decomposition
status: Refined
created: 2026-09-28
dependencies:
- TASK-0213
- TASK-0214
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0065
- US-0066
target_release: 0.8.0
---

# TASK-0287: Frontend App Shell Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `frontend/test/app-shell.test.ts` (378 lines, 75.6% of limit) into modular TypeScript test submodules under `frontend/test/app_shell/` (`routing.test.ts`, `session-transitions.test.ts`, `websocket-lifecycle.test.ts`, `state-breadcrumbs.test.ts`), ensuring all test modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`frontend/test/app-shell.test.ts` is the second-largest source file in the entire repository and the single largest test file in `frontend/`. It consolidates dynamic view resolution, route parameter extraction, staging lobby-to-live session view transitions, route-bound WebSocket lifecycle management, and breadcrumb state updates into a monolithic 378-line suite. As new route-bound views and modal workflows are added to the App Shell, this file will rapidly approach the 500-line invariant limit unless modularized.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: Deep-link routing, route resolution, parameter extraction, and navigation lifecycle.
  - `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md`: View staging transitions, route-bound WebSocket lifecycles, and component state teardown.
  - `docs/reference/design-tokens-and-themes.md`: Bauhaus visual hierarchy and breadcrumb navigation tokens.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: App Shell component lifecycle and view orchestration.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: View state styling and navigation hierarchy.
  - **ADR-0013: Frontend Microfrontend Architecture**: Decoupled view composition and route-bound lifecycle.

## Scope of Work & Implementation Plan
1. **Dynamic Routing & Parameter Extraction (`frontend/test/app_shell/routing.test.ts`)**:
   - Extract login/register view resolution, campaign dashboard routes, campaign-detail parameter extraction, and route fallback assertions (< 110 lines).
2. **Session Lifecycle & Transitions (`frontend/test/app_shell/session-transitions.test.ts`)**:
   - Extract staging lobby resolution, active VTT view transitions, character assignment updates, and deep-link routing tests (< 110 lines).
3. **WebSocket Lifecycle Management (`frontend/test/app_shell/websocket-lifecycle.test.ts`)**:
   - Extract route-bound WebSocket connection requirements, active view teardown, and session channel switching tests (< 100 lines).
4. **State & Breadcrumbs Orchestration (`frontend/test/app_shell/state-breadcrumbs.test.ts`)**:
   - Extract active view state transitions, breadcrumb trail updates, dynamic title resolution, and browser history assertions (< 100 lines).
5. **Verification**:
   - Safely remove monolithic `frontend/test/app-shell.test.ts` and ensure `npm test` runs all submodules with 100% passing rate.

## INVEST Criteria Evaluation
- **Independent (I)**: Test reorganization is self-contained within `frontend/test/app_shell/` without modifying production App Shell behavior.
- **Negotiable (N)**: Test submodule boundaries and test helper organization can be tuned cleanly.
- **Valuable (V)**: Prevents the largest frontend test suite from breaching Hard Invariant 6 (500 lines) and improves frontend test isolation and maintainability.
- **Estimable (E)**: Discrete test scenario grouping with known line counts and existing passing coverage.
- **Small (S)**: Each extracted test file will be strictly < 130 lines.
- **Testable (T)**: Directly executable via `npm test` in `frontend/` with 100% assertions passing.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `frontend/test/app-shell.test.ts` decomposed into modular submodules under `frontend/test/app_shell/`:
   - `frontend/test/app_shell/routing.test.ts` (< 130 lines)
   - `frontend/test/app_shell/session-transitions.test.ts` (< 130 lines)
   - `frontend/test/app_shell/websocket-lifecycle.test.ts` (< 130 lines)
   - `frontend/test/app_shell/state-breadcrumbs.test.ts` (< 130 lines)
2. All extracted test modules strictly satisfy Hard Invariant 6 (< 130 lines).
3. All tests pass with 100% success rate via frontend test runner (`npm test` in `frontend/`).
4. Monolithic `frontend/test/app-shell.test.ts` safely removed.
5. All TypeScript lints pass cleanly.
