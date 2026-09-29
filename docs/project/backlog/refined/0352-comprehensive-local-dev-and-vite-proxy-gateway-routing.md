---
id: '0352'
title: Comprehensive Local Development Command (make dev) and Vite Proxy Gateway Routing
status: Refined
created: 2026-09-28
dependencies:
- TASK-0000
- TASK-0008
- TASK-0027
governing_adrs:
- ADR-0004
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0001
- PRD-0023
governing_stories:
- US-0001
- US-0065
target_release: 0.9.0
---

# TASK-0352: Comprehensive Local Development Command (make dev) and Vite Proxy Gateway Routing

## Status
Refined

## Summary
Implement a unified, robust `make dev` workflow in the root `Makefile` that starts the API Gateway (`dev-api`), background inference worker, and hot-reloading Vite frontend (`dev-frontend`) concurrently with health check gating. Expand `frontend/vite.config.ts` proxy configuration to route all backend API paths (`/api`, `/api/v1`, `/ws`, `/docs`, `/openapi.json`, `/mail`, `/oauth`) to their respective local services, eliminating `502 Bad Gateway` errors and un-proxied endpoint failures.

## Problem Statement
Currently, running `make dev-frontend` starts Vite on `http://localhost:5173`, but leaves the backend API Gateway (`localhost:8000`), SpiceDB, Zitadel, and microservices unstarted. There is no unified `make dev` target in `Makefile`. Consequently, all API calls made by the frontend to `/api/v1/...` return `502 Bad Gateway` or connection refused, forcing the App Shell to drop into static fixture fallbacks that fail to reflect newly created resources or route mutations.

Furthermore, `frontend/vite.config.ts` only proxies `/api/v1` and `/ws` to `localhost:8000`. Direct service endpoints that do not use `/api/v1` (such as `/campaigns/{id}/settlements`, `/docs`, `/openapi.json`, Mailpit at `/mail` on port 8025, or Zitadel at `/oauth` on port 8080) are intercepted by Vite as client SPA navigation routes and incorrectly served `index.html`.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/tutorials/01-local-development-setup.md`: Local Kind cluster, Helm stack, UV monorepo, and Storybook dev setup.
  - `docs/reference/ports-and-endpoints.md`: Ingress routing table, gateway ports (8000), Vite (5173), Mailpit (8025), Zitadel (8080), and microservice ports.
  - `docs/reference/cli-interfaces.md`: Developer tooling, `Makefile` targets, and UV workspace commands.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: App Shell development environment and proxy behavior.
  - **ADR-0010: Real-time Audio and Tactical Board Synchronization**: Sub-500ms WebSocket and HTTP pipelines.
  - **ADR-0013: Frontend Microfrontend Architecture**: Unified gateway aggregation and microfrontend consumption.

## Scope of Work & Implementation Plan
1. **Root `Makefile` Enhancement (`make dev`)**:
   - Add a high-level `.PHONY: dev` target in `Makefile`.
   - Implement concurrent execution using process management or a lightweight background orchestrator script (`scripts/dev_server.py` or concurrent subshells):
     - Start API Gateway (`uv run python gateway/api/src/gateway_api/main.py`) on port 8000.
     - Wait for Gateway HTTP health check (`http://localhost:8000/api/v1/health` or `/healthz`) before starting Vite.
     - Start Vite frontend (`cd frontend && CHOKIDAR_USEPOLLING=true pnpm run dev`) on port 5173.
     - Trap `SIGINT` / `SIGTERM` to cleanly terminate all child processes upon exit.
2. **Vite Proxy Expansion (`frontend/vite.config.ts`)**:
   - Expand `server.proxy` entries:
     - `/api/v1` -> `http://localhost:8000` (changeOrigin: true).
     - `/api` -> `http://localhost:8000` (changeOrigin: true).
     - `/ws` -> `ws://localhost:8000` (ws: true).
     - `/docs` and `/openapi.json` -> `http://localhost:8000`.
     - `/mail` -> `http://localhost:8025` (Mailpit mock SMTP UI).
   - Ensure WebSocket upgrades on `/ws` are properly handled with reconnect tolerance.
3. **Gateway Health & CORS Readiness**:
   - Verify `gateway/api/src/gateway_api/main.py` permits CORS requests from `http://localhost:5173` with full headers and methods.
4. **Verification**:
   - Execute `make dev` in a terminal; verify Gateway starts, health check passes, and Vite serves `http://localhost:5173` without 502 proxy errors.
   - Run blackbox tests in `tests/test_blackbox_dev_environment.py` asserting gateway reachability through the Vite proxy.

## INVEST Criteria Evaluation
- **Independent (I)**: Self-contained within `Makefile`, `frontend/vite.config.ts`, and local orchestration scripts.
- **Negotiable (N)**: Process orchestration approach (concurrent bash trap vs python supervisor) can be adjusted cleanly.
- **Valuable (V)**: Eliminates 502 Bad Gateway errors for all local development, restoring live API connectivity and removing mock fallbacks.
- **Estimable (E)**: Known configuration targets and standard Node/Python orchestration patterns.
- **Small (S)**: Confined to Makefile, Vite config, and dev launcher script (< 150 lines).
- **Testable (T)**: Directly testable via `curl` through Vite proxy and automated dev script health check.

## Definition of Done
1. `make dev` exists in root `Makefile` and is documented in `make help`.
2. Running `make dev` successfully boots the API Gateway and Vite frontend concurrently with clean exit handling.
3. Requests to `http://localhost:5173/api/v1/...` and `http://localhost:5173/api/...` proxy seamlessly to the API Gateway without 502 Bad Gateway responses.
4. Requests to `http://localhost:5173/mail` proxy to Mailpit when available.
5. All source files remain strictly under 500 lines per Hard Invariant 6.
