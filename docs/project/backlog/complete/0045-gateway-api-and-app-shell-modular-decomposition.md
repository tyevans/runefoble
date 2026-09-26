---
id: '0045'
title: Gateway API Router and App Shell Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0008
- TASK-0012
- TASK-0027
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0007
- ADR-0009
- ADR-0013
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/42
---
# TASK-0045: Gateway API Router and App Shell Modular Decomposition

## Status
Refined

## Summary
Decompose monolithic orchestration files in `gateway/api/src/gateway_api/main.py` (399 lines) and `frontend/src/runefoble-app.ts` (471 lines, 94.2% of limit) into modular subcomponents and router controllers to strictly adhere to Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
Health scans identify `frontend/src/runefoble-app.ts` at 471 lines (highest in repository) and `gateway/api/src/gateway_api/main.py` at 399 lines:
- `frontend/src/runefoble-app.ts` bundles top-level shell layout styles, brand navigation headers, campaign selector modals, spectator mode transitions, toast notifications, and microfrontend component composition into one monolithic Lit element.
- `gateway_api/main.py` bundles FastAPI application initialization, OpenAPI tags metadata, CORS configuration, Redis event bus lifecycle hooks, campaign WebSocket endpoint routing, spectator session proxying, and direct campaign CRUD/role endpoints into a single file.

Without modular decomposition, any addition of live voice room controls or spectator chat will breach Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace for Python Bounded Contexts.
- **ADR-0004**: Lit Web Components and Storybook UI (encapsulated components with Shadow DOM).
- **ADR-0007**: API Gateway Architecture with FastMCP and WebSockets.
- **ADR-0009**: Code Quality and Linting with Ruff (file length limit < 500 lines).
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring.

## Proposed Decomposition
1. **Gateway API Modular Routers (`gateway/api/src/gateway_api/routers/`)**:
   - `routers/campaigns.py`: Campaign CRUD endpoints, participant role assignments, and SpiceDB checks (~120 lines).
   - `routers/spectator.py`: Spectator state sanitization and public spectator proxy endpoints (~90 lines).
   - `routers/health.py`: Liveness/readiness probes, upstream service health, and event bus connectivity checks (~60 lines).
   - `gateway/api/src/gateway_api/main.py`: Reduced to an application shell mounting routers and configuring CORS/lifespan (< 120 lines).
2. **App Shell Subcomponents (`frontend/src/components/`)**:
   - `components/runefoble-header.ts`: Navigation bar, brand logo, status indicators, and settings button (< 130 lines).
   - `components/runefoble-campaign-nav.ts`: Campaign selector modal, session status badges, and role chips (< 120 lines).
   - `styles/app-shell.styles.ts`: Extract static CSS styles and Bauhaus layout tokens (< 160 lines).
   - `frontend/src/runefoble-app.ts`: Lightweight coordinator (< 180 lines) managing routing and active view modes.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal code organization without altering public HTTP endpoints, WebSocket contracts, or microfrontend manifest contracts.
- **Negotiable (N)**: Specific subcomponent boundaries and CSS token extraction strategies can be adapted.
- **Valuable (V)**: Protects against file length limit violations (Hard Invariant 6) as future features expand gateway and shell capabilities.
- **Estimable (E)**: Standard FastAPI router extraction and Lit component composition.
- **Small (S)**: Confined to gateway router refactoring and Lit shell modularization; all resulting files < 200 lines.
- **Testable (T)**: Existing gateway blackbox integration tests and frontend build/Storybook tests verify identical functional behavior.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Code Extraction**:
   - `gateway/api/src/gateway_api/main.py` decomposed into `routers/campaigns.py`, `routers/spectator.py`, and `routers/health.py`.
   - `frontend/src/runefoble-app.ts` decomposed into `components/runefoble-header.ts`, `components/runefoble-campaign-nav.ts`, and `styles/app-shell.styles.ts`.
2. **File Length Compliance (Hard Invariant 6)**:
   - All touched and newly created files strictly under 250 lines.
3. **Frontdoor Blackbox Verification**:
   - 100% pass on gateway blackbox tests: `uv run pytest tests/test_gateway.py tests/test_blackbox_gateway_zanzibar.py tests/test_blackbox_websocket_zanzibar.py`.
4. **Frontend Build & Storybook Integrity**:
   - Passes `pnpm run build` with zero TypeScript errors.
   - Storybook stories render cleanly without console warnings.
5. **Static Analysis & Linting**:
   - Passes `uv run ruff check gateway/api` and `uv run ruff format --check gateway/api`.
