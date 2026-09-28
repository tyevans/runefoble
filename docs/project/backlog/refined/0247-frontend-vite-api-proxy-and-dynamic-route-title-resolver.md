---
id: '0247'
title: Frontend Vite API Proxy and Dynamic Route Title Resolver
status: Refined
created: 2026-09-27
dependencies:
- TASK-0206
governing_adrs:
- ADR-0004
- ADR-0005
- ADR-0012
governing_prds:
- PRD-0023
governing_stories:
- US-0066
- US-0068
target_release: 0.8.0
---
# TASK-0247: Frontend Vite API Proxy and Dynamic Route Title Resolver

## Status
Refined

## Summary
Configure the Vite development server in `frontend/vite.config.ts` to proxy `/api/v1` and `/ws` to the local Gateway API server (`http://localhost:8000`), and refactor `frontend/src/router/router.ts` with asynchronous dynamic title resolution so breadcrumbs and headers display real campaign and session names loaded from live API records instead of hardcoded stub IDs ('4', '5').

## Problem Statement
In local development on `http://localhost:5173`, all REST API requests issued by `AppDataService` fail with HTTP 404 because Vite is not configured with a reverse proxy to `http://localhost:8000`. This forces every view into static client mock fallbacks. Furthermore, when visiting a campaign page like `http://localhost:5173/#/campaigns/camp-1790564858218`, the title resolver only checks for IDs `'4'` and `'5'`, resulting in an unpolished `"Campaign #camp-1790564858218"` breadcrumb label.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/tutorials/01-local-development-setup.md`: Local development environment and port mapping.
  - `docs/reference/ports-and-endpoints.md`: Ingress routing table and microservice ports.
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: SPA client-side routing and breadcrumb patterns.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Frontend development architecture.
  - **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: Local developer port alignment.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Dynamic breadcrumbs and header titles.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Stories**:
  - [`us-0066-client-side-routing-navigation-and-breadcrumbs.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)
  - [`us-0068-app-shell-view-audit-and-api-proxying.md`](../../user_stories/accepted/us-0068-app-shell-view-audit-and-api-proxying.md)

## Detailed Specification & Implementation Plan
1. **Vite Development Proxy Configuration (`frontend/vite.config.ts`)**:
   - Add `server.proxy` mapping `/api/v1` to `target: 'http://localhost:8000'`, `changeOrigin: true`.
   - Add `server.proxy` mapping `/ws` to `target: 'ws://localhost:8000'`, `ws: true`.
   - Support environment variable override (`process.env.GATEWAY_API_URL || 'http://localhost:8000'`).
2. **Dynamic Route Title Resolution (`frontend/src/router/router.ts`)**:
   - Extend `Router` with an asynchronous title resolver cache (`setAsyncTitleResolver(fn: (type, id) => Promise<string | undefined>)`).
   - Cache resolved entity titles (`Map<string, string>`) so breadcrumbs update immediately without flashing raw IDs.
   - Wire `runefoble-app.ts` to register the title resolver against `appDataService.fetchCampaign(id)` and `appDataService.fetchSession(id)`.
3. **Blackbox Router Tests (`frontend/test/router.test.ts`)**:
   - Verify proxy target definitions in Vite configuration.
   - Verify router resolves dynamic titles asynchronously and updates breadcrumb models upon navigation.

## INVEST Criteria Evaluation
- **Independent (I)**: Changes are isolated to Vite configuration and client router utilities without touching backend services.
- **Negotiable (N)**: Cache eviction strategy and TTL for resolved titles can be tuned.
- **Valuable (V)**: Unlocks live backend communication in Vite development and eliminates stub title labels.
- **Estimable (E)**: Straightforward Vite proxy configuration and router cache expansion.
- **Small (S)**: Kept strictly under 100 lines of changes.
- **Testable (T)**: Frontdoor unit and component tests verify proxy configuration exports and async breadcrumb updates.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `frontend/vite.config.ts` proxies `/api/v1` and `/ws` to `http://localhost:8000`.
2. Router resolves real entity titles dynamically and updates breadcrumbs.
3. Tests in `frontend/test/router.test.ts` pass with zero regressions.
4. Source files strictly adhere to file length limit (<500 lines).
