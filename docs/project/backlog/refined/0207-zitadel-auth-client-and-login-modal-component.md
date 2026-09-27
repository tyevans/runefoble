---
id: '0207'
title: Zitadel Auth Client and Login Modal Component
status: Refined
created: 2026-09-27
dependencies:
- TASK-0206
governing_adrs:
- ADR-0004
- ADR-0005
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0062
target_release: 0.8.0
---

# TASK-0207: Zitadel Auth Client and Login Modal Component

## Status
Refined

## Summary
Implement a browser-side authentication service and Lit Web Component `<runefoble-auth-modal>` in `frontend/src/auth/`, providing user registration, login, token management (JWT storage/refresh), and user menu controls.

## Problem Statement
Users cannot register or log into Runefoble through the frontend. All gateway requests currently rely on hardcoded developer test headers, and there is no UI component for sign-up, sign-in, user avatar display, or logging out.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/authenticate-with-zitadel-oidc.md`: JWT verification, claims structure, and token lifecycles.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit component standards and story co-location.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: UI presentation and event emission.
  - **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: Zitadel OIDC token provider.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Form inputs, modals, and buttons styled with Bauhaus design tokens.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Decoupled auth state provider.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Story**: [`us-0062-user-registration-zitadel-auth-and-profile.md`](../../user_stories/accepted/us-0062-user-registration-zitadel-auth-and-profile.md)

## Detailed Specification & Implementation Plan
1. **Frontend Auth Service (`frontend/src/auth/auth-service.ts`)**:
   - Manage Zitadel OIDC token exchange (with local dev fallback proxy support).
   - LocalStorage persistence for access token, refresh token, and claims (`user_id`, `username`, `email`, `roles`).
   - Token expiry monitor and silent token refresh.
   - Event emitter notifying UI of auth state changes (`@rf-auth-changed`).
2. **Auth Modal & User Menu Component (`frontend/src/components/runefoble-auth-modal.ts` & `frontend/src/components/runefoble-user-menu.ts`)**:
   - Modal supporting "Sign In" and "Sign Up" tabs with form validation and error handling.
   - User avatar badge with dropdown menu: user name, email, roles, "Account Settings", and "Sign Out" button.
3. **Storybook Stories (`frontend/src/stories/runefoble-auth-modal.stories.ts`)**:
   - Stories demonstrating unauthenticated modal, validation errors, and authenticated user menu across all themes.

## INVEST Criteria Evaluation
- **Independent (I)**: Auth service and modal can be tested in Storybook with mock token exchanges independently of backend deployment.
- **Negotiable (N)**: Form layout and avatar display style can be customized via CSS variables.
- **Valuable (V)**: Delivers true user identity and login/logout capabilities, ending reliance on hardcoded mock identities.
- **Estimable (E)**: Pure frontend Lit component and browser service sized for a single `agy -p` pass.
- **Small (S)**: `auth-service.ts` (<220 lines), `runefoble-auth-modal.ts` (<240 lines), `runefoble-user-menu.ts` (<180 lines).
- **Testable (T)**: Frontdoor blackbox tests verify credential exchange, token storage, and UI state updates.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Auth service implemented in `frontend/src/auth/auth-service.ts` (<220 lines).
2. Auth modal and user menu components authored in `frontend/src/components/` (<240 lines each).
3. Storybook stories render without console errors in dark and light modes.
4. Unit tests verify login flow and token storage without leaking sensitive credentials.
