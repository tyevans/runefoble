---
id: '0660'
title: Helm Ingress Routes WebSocket Paths to the Gateway and Docs Name Them
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0005
- ADR-0006
- ADR-0013
governing_prds:
- PRD-0005
governing_stories:
- US-0014
target_release: 0.9.0
---

# TASK-0660: Helm Ingress Routes WebSocket Paths to the Gateway and Docs Name Them

## Status
Complete

## Summary
The gateway serves WebSocket routes at `/ws/...` (for example `/ws/session/{id}`, `/ws/voice/{id}`, `/ws/boards/{id}`, and `/ws/campaigns/{id}`). The Helm ingress has no `/ws` path, so through Traefik those requests reach the frontend container, which serves only static files. The reference docs say `/api` is the REST and WebSocket gateway. Add the `/ws` ingress route to the Helm chart, and correct the ingress tables and the architecture diagram.

## Problem Statement
- `docs/reference/ports-and-endpoints.md:8` says `/api` is the "REST and WebSocket API gateway". The WebSocket routes are at `/ws/...`.
- `deployments/helm/runefoble/values.yaml` ingress (lines 14-41 show `/api`, `/docs`, `/swagger-ui`, `/auth`, `/analytics`, `/mail`, `/mailpit`) has no `/ws` path.
- `frontend/nginx.conf:5` has only `location /`. The frontend opens `new WebSocket(...)` to `/ws/session/...` on the same host (`frontend/src/runefoble-app.ts:106`), which Traefik sends to the frontend.
- `docs/reference/architecture-overview.md` shows the same ingress picture without `/ws`.
- P4 (low): `frontend/vite.config.ts` proxies `/healthz`. `docs/reference/ports-and-endpoints.md` does not list it.
- `w2-soundscape.md` and `w2-asset-forge.md` report that the ingress sends only `/api` to the gateway, so their services are unreachable through the ingress. Those services are out of scope here, but the ingress change must not break their current paths.

## Documentation & Architecture Review
- ADR-0005: ingress is a Helm concern. Add the route in the umbrella chart only.
- ADR-0013: the frontend reaches services through the gateway. WebSockets follow the same rule.
- Concurrent work: TASK-0508 (gateway voice duplex routing) and TASK-0456 (OBS bridge) touch WebSocket routing in the gateway. This task changes only the ingress and the docs.
- `docs/how-to/authenticate-with-zitadel-oidc.md` describes WebSocket authentication. Link it from the ingress docs.

## Product & User Story References
- [`us-0014-realtime-board-websocket-sync.md`](../../user_stories/accepted/us-0014-realtime-board-websocket-sync.md)
- [`prd-0005-realtime-websocket-board-sync.md`](../../product/accepted/prd-0005-realtime-websocket-board-sync.md)

## Detailed Specification & Implementation Plan
1. Add an ingress path `/ws` (`pathType: Prefix`) that points to `gateway-api` port 8000 in `deployments/helm/runefoble/values.yaml`. Place it before the frontend catch-all.
2. Check the Traefik annotations for WebSocket upgrade support. Add any annotation the chart needs for upgrade.
3. Update `docs/reference/ports-and-endpoints.md`: the ingress table gets a `/ws` row, and line 8 names the paths.
4. Update the diagram and text in `docs/reference/architecture-overview.md`.
5. Remove the blank lines that split the tables in `ports-and-endpoints.md` (lines 100, 118, 204, 298), so the rows render. This is part of the same file edit.
5a. Add the `/healthz` Vite proxy row to `ports-and-endpoints.md` (P4).
6. Check the Vite dev proxy (`frontend/vite.config.ts`) forwards `/ws` with `ws: true`. Change it only if it does not.
7. Do not change the gateway code in this task.

## Frontdoor Blackbox Test Plan
- `helm template runefoble ./deployments/helm/runefoble` renders an ingress rule for `/ws` that targets `gateway-api` on port 8000. A pytest check (`tests/test_blackbox_helm_ingress_ws.py`) runs `helm template`, parses the ingress, and asserts the path. Before the change it FAILS. After the change it PASSES.
- Local stack check (manual, recorded in the task file): a WebSocket client connects to `ws://localhost/ws/session/{id}` through Traefik and receives the gateway's handshake, not the frontend's HTML response.
- The check uses only the public ingress. No direct service access.

## Definition of Done
1. The ingress renders a `/ws` rule to `gateway-api`. `helm lint` and `helm template` pass.
2. `docs/reference/ports-and-endpoints.md` and `docs/reference/architecture-overview.md` name the `/ws` path and match the chart.
3. The manual WebSocket check is recorded in the task file.
4. The Vite dev proxy forwards `/ws` with upgrade support (verified by a dev run or a config test).
5. Blank lines are removed from the four affected tables in `ports-and-endpoints.md`, and the `/healthz` row is added.
6. Files stay under 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w3-docs-integrity.md`, `w2-soundscape.md`, `w2-asset-forge.md`
