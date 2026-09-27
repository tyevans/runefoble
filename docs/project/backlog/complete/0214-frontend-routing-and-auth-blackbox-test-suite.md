---
id: '0214'
title: Frontend Routing and Auth Blackbox Test Suite
status: Complete
created: 2026-09-27
dependencies:
- TASK-0206
- TASK-0207
- TASK-0213
governing_adrs:
- ADR-0004
- ADR-0005
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0062
- US-0066
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/206
---
# TASK-0214: Frontend Routing and Auth Blackbox Test Suite

## Status
Refined

## Summary
Implement a blackbox frontdoor test suite verifying client-side SPA routing, deep-link parameter parsing, authentication guards, and token persistence without backdoor DOM or state manipulation.

## Problem Statement
Routing and authentication transitions across views represent critical failure surfaces. Without frontdoor test coverage, regressions in URL hash parsing, route redirection guards, or token expiry handling could break access for users.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/develop-lit-components-in-storybook.md`: Component testing standards.
  - `docs/how-to/authenticate-with-zitadel-oidc.md`: Auth flow test patterns.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Component testing standards.
  - **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: Zitadel token verification.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Blackbox testing through public element interfaces.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Story**: [`us-0062-user-registration-zitadel-auth-and-profile.md`](../../user_stories/accepted/us-0062-user-registration-zitadel-auth-and-profile.md)
- **User Story**: [`us-0066-client-side-routing-navigation-and-breadcrumbs.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)

## Detailed Specification & Implementation Plan
1. **Router & Deep-Link Blackbox Tests (`frontend/tests/blackbox-routing-auth.test.ts`)**:
   - Verify matching of hash paths (`#/campaigns`, `#/campaigns/42/sessions/108`).
   - Verify route parameter extraction (`campaignId`, `sessionId`).
   - Verify browser history navigation (forward/back).
2. **Auth Guard & Session Persistence Tests**:
   - Verify unauthenticated visitor visiting `#/campaigns` redirects to `#/login`.
   - Verify valid token in localStorage permits direct access to protected routes.
   - Verify token clearing triggers redirection to login.

## INVEST Criteria Evaluation
- **Independent (I)**: Test suite runs independently through npm/pnpm test runner.
- **Negotiable (N)**: Test assertions focus strictly on observable URL and DOM state.
- **Valuable (V)**: Guarantees rock-solid navigation and prevents authentication bypass bugs.
- **Estimable (E)**: Standard Vitest/Playwright or jsdom test file sized within one pass.
- **Small (S)**: Test module is strictly <250 lines, adhering to Hard Invariant 6.
- **Testable (T)**: Directly executes and reports test pass/fail results.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Test suite implemented in `frontend/tests/blackbox-routing-auth.test.ts` (<250 lines).
2. Verifies all scenarios in US-0062 and US-0066.
3. Tests interact strictly through public DOM methods, window hash events, and localStorage interfaces.
4. Adheres to file length invariant (<500 lines).
