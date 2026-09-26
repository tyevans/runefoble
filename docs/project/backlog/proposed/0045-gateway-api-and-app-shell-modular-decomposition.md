---
id: '0045'
title: Gateway API Router and App Shell Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0008, TASK-0012, TASK-0027]
governing_adrs: [ADR-0004, ADR-0007, ADR-0013]
target_release: 0.2.0
---

# TASK-0045: Gateway API Router and App Shell Modular Decomposition

## Status
Proposed

## Summary
Decompose monolithic orchestration files in `gateway/api/src/gateway_api/main.py` (397 lines) and `frontend/src/runefoble-app.ts` (397 lines) into modular subcomponents and router controllers before they breach Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
Health scans identify `gateway/api/src/gateway_api/main.py` (397 lines, 79.4% of limit) and `frontend/src/runefoble-app.ts` (397 lines, 79.4% of limit) rapidly approaching the 400-line warning threshold and the 500-line hard ceiling.
- `gateway_api/main.py` combines FastAPI application initialization, OpenAPI tags metadata, CORS configuration, Redis event bus lifecycle hooks, campaign WebSocket endpoint routing, spectator session proxying, and direct campaign CRUD/role endpoints into a single file.
- `runefoble-app.ts` bundles top-level shell layout styles, navigation headers, campaign selector modals, spectator mode transitions, toast notifications, and microfrontend component composition into one monolithic Lit element.

## Proposed Decomposition
1. **Gateway API Decomposition (`gateway/api/src/gateway_api/routers/`)**:
   - `routers/campaigns.py`: Campaign CRUD endpoints and role assignment handlers.
   - `routers/spectator.py`: Spectator state sanitization and public spectator proxy endpoints.
   - `routers/health.py`: Readiness/liveness probes and event bus connectivity checks.
   - Reduce `gateway_api/main.py` to a clean orchestration shell (< 100 lines) mounting sub-routers.
2. **App Shell Decomposition (`frontend/src/`)**:
   - `components/runefoble-header.ts`: Brand header, navigation links, and theme switcher integration.
   - `components/runefoble-campaign-nav.ts`: Campaign selector modal and participant role chips.
   - `styles/app-shell.css.ts`: Extract static CSS styles and Bauhaus layout tokens.
   - Reduce `runefoble-app.ts` to < 180 lines, focusing strictly on high-level routing and view mode state.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal code organization without altering public HTTP endpoints, WebSocket contracts, or microfrontend manifest contracts.
- **Negotiable (N)**: Specific subcomponent boundaries and CSS token extraction strategies can be adapted.
- **Valuable (V)**: Protects against file length limit violations (Hard Invariant 6) as future voice room and live board features expand gateway and shell capabilities.
- **Estimable (E)**: Standard FastAPI router extraction and Lit component composition.
- **Small (S)**: Confined to gateway router refactoring and Lit shell modularization; all resulting files < 200 lines.
- **Testable (T)**: Existing gateway blackbox integration tests and frontend build/Storybook tests verify identical functional behavior.

## Acceptance Criteria
1. Zero changes to public HTTP status codes, routes, or WebSocket payloads.
2. All modified and newly created source files strictly under 250 lines.
3. 100% test pass rate across `tests/` and frontend test/build suites.
