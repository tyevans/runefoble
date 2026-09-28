---
id: '0251'
title: App Shell Views Enumeration, Wiring Audit, and Blackbox Test Suite
status: Refined
created: 2026-09-27
dependencies:
- TASK-0247
- TASK-0250
governing_adrs:
- ADR-0004
- ADR-0010
- ADR-0012
governing_prds:
- PRD-0023
governing_stories:
- US-0066
- US-0068
target_release: 0.8.0
---

# TASK-0251: App Shell Views Enumeration, Wiring Audit, and Blackbox Test Suite

## Status
Refined

## Summary
Develop a comprehensive blackbox E2E and component test suite (`frontend/test/app-shell-views-wiring-audit.test.ts` and `tests/test_blackbox_app_shell_views_audit.py`) that systematically enumerates every defined application route, auditing for correct view mounting, dynamic title resolution, parameter extraction, route-bound WebSocket lifecycles, and error fallbacks.

## Problem Statement
The App Shell supports nine standard route patterns (`#/login`, `#/register`, `#/campaigns`, `#/campaigns/:id`, `#/campaigns/:id/characters`, `#/campaigns/:id/lobby/:id`, `#/campaigns/:id/sessions/:id`, `#/characters`, `#/profile`). Several of these routes previously had route collisions or missing view handlers (e.g. `#/profile` defaulting to campaigns, `#/campaigns/:id/characters` colliding with campaign-detail). A systematic regression test suite is required to guarantee every defined route mounts its dedicated component without unhandled exceptions or broken mock fallbacks.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: SPA route catalog and test patterns.
  - `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md`: View state lifecycle, transition teardown, and WebSocket management.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit component DOM assertions and theme token propagation.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Component mounting and DOM assertions.
  - **ADR-0010: Continuous Integration Pipeline**: Fast, deterministic frontend automated tests.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Preserving visual token invariants across views.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Story**: [`us-0068-app-shell-view-audit-and-api-proxying.md`](../../user_stories/accepted/us-0068-app-shell-view-audit-and-api-proxying.md)

## Detailed Specification & Implementation Plan
1. **Route Enumeration Matrix**:
   - Write tests parameterized across all nine standard routes:
     - `#/login` mounts auth modal.
     - `#/register` mounts auth modal with registration tab.
     - `#/campaigns` mounts `<runefoble-campaign-dashboard>`.
     - `#/campaigns/:id` mounts `<runefoble-campaign-header>`, members, and session list.
     - `#/campaigns/:id/characters` mounts party character roster.
     - `#/campaigns/:id/lobby/:id` mounts `<runefoble-session-lobby>`.
     - `#/campaigns/:id/sessions/:id` mounts tactical board and active game components.
     - `#/characters` mounts personal character roster.
     - `#/profile` mounts user settings panel.
2. **WebSocket Lifecycle Assertions**:
   - Verify WebSocket connects only when entering `session-lobby` or `session-active` routes.
   - Verify WebSocket disconnects and disposes event listeners when transitioning back to `#/campaigns` or `#/profile`.
3. **Dynamic Title and Breadcrumb Verification**:
   - Assert dynamic campaign and session titles populate in breadcrumb trail without raw ID fallbacks.

## INVEST Criteria Evaluation
- **Independent (I)**: Test suite runs independently in the frontend test runner and pytest suite.
- **Negotiable (N)**: Mock fixtures and timing thresholds can be adjusted.
- **Valuable (V)**: Prevents regressions across all current and future views in the App Shell.
- **Estimable (E)**: Standard frontdoor testing matrix sized for a single pass.
- **Small (S)**: Test file modularized and kept strictly under 350 lines.
- **Testable (T)**: Frontdoor assertions test observable DOM state and router events.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `frontend/test/app-shell-views-wiring-audit.test.ts` and `tests/test_blackbox_app_shell_views_audit.py` implemented and passing.
2. All nine standard routes tested for view mounting and breadcrumbs.
3. WebSocket lifecycle verified on route transitions.
4. All source files strictly adhere to file length limit (<500 lines).
