---
id: '0206'
title: Frontend SPA Client Router and Navigation Chrome
status: Refined
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0066
target_release: 0.8.0
---

# TASK-0206: Frontend SPA Client Router and Navigation Chrome

## Status
Refined

## Summary
Implement a lightweight, dependency-free client-side Single Page Application (SPA) router and top-level navigation chrome in `frontend/src/router/`, enabling deep-linkable URLs, dynamic breadcrumb generation, view history, and route-aware lifecycle cleanup.

## Problem Statement
The frontend currently lacks any client-side routing mechanism. `runefoble-app.ts` unconditionally renders a hardcoded demo page for a single session, preventing users from bookmarking views, navigating between campaigns and sessions, or using standard browser forward/back buttons.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit component standards and story co-location.
  - `docs/reference/design-tokens-and-themes.md`: Bauhaus typography, border tokens, and CSS variables.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Component encapsulation and reactive properties.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Dynamic breadcrumbs and header styling with Bauhaus design tokens.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: App Shell decoupling and view container coordination.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Story**: [`us-0066-client-side-routing-navigation-and-breadcrumbs.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)

## Detailed Specification & Implementation Plan
1. **Lightweight SPA Client Router (`frontend/src/router/router.ts`)**:
   - Hash-based / history route pattern matcher supporting routes:
     - `#/login` and `#/register`
     - `#/campaigns` (Dashboard)
     - `#/campaigns/:campaignId` (Campaign Details)
     - `#/campaigns/:campaignId/characters` (Campaign Party)
     - `#/campaigns/:campaignId/lobby/:sessionId` (Pre-Game Lobby)
     - `#/campaigns/:campaignId/sessions/:sessionId` (Active VTT Session)
     - `#/characters` (Personal Character Roster)
     - `#/profile` (User Profile)
   - Route change event dispatcher (`@route-changed`) notifying the App Shell.
   - Route guard callbacks for authentication checks.
2. **Dynamic Breadcrumb Navigation Component (`frontend/src/components/runefoble-breadcrumbs.ts`)**:
   - Lit Web Component (`<runefoble-breadcrumbs>`) rendering hierarchical clickable breadcrumb segments (e.g. `Campaigns > Tomb of the Star-Eater > Lobby 15`).
   - High-contrast Bauhaus typography and hover states.
3. **Storybook Stories (`frontend/src/stories/runefoble-breadcrumbs.stories.ts`)**:
   - Stories demonstrating root, campaign, lobby, and session breadcrumb hierarchies with theme switching.

## INVEST Criteria Evaluation
- **Independent (I)**: Router module and breadcrumbs component operate independently without depending on backend API changes.
- **Negotiable (N)**: Hash vs. History API fallback and route parameter syntax can be adjusted.
- **Valuable (V)**: Unlocks bookmarkable deep links, multi-view navigation, and browser history for all players and GMs.
- **Estimable (E)**: Pure frontend TypeScript and Lit Web Component implementation sized within a single `agy -p` pass.
- **Small (S)**: Both `router.ts` and `runefoble-breadcrumbs.ts` are strictly <250 lines, adhering to Hard Invariant 6.
- **Testable (T)**: Frontdoor blackbox tests verify route transitions, parameter parsing, and history events.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. SPA router module created in `frontend/src/router/router.ts` (<250 lines).
2. Breadcrumbs component implemented in `frontend/src/components/runefoble-breadcrumbs.ts` (<180 lines).
3. Storybook stories for breadcrumbs pass with zero console errors in dark and light modes.
4. Unit tests verify route matching and deep-linking parameters without external dependencies.
