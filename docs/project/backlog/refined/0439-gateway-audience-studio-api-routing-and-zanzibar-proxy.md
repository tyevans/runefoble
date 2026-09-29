---
id: '0439'
title: Gateway Audience Studio API Routing & Zanzibar Authorization Proxy
status: Refined
created: 2026-09-29
dependencies:
- TASK-0008
- TASK-0051
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0011
- PRD-0023
governing_stories:
- US-0006
- US-0030
- US-0031
target_release: 0.9.0
---

# TASK-0439: Gateway Audience Studio API Routing & Zanzibar Authorization Proxy

## Status
Refined

## Summary
Implement a unified API Gateway proxy router (`gateway/api/src/gateway_api/routers/audience.py`) that routes REST requests (`/api/v1/audience/*`) and WebSocket connections (`/ws/audience/{campaign_id}`) to the `audience-studio` microservice (`http://audience-studio:8010`). Enforce SpiceDB Zanzibar permission checks (`can_manage_audience_polls`, `can_approve_audience_chaos`) on DM administrative mutators (poll lifecycle, proposal approval, proposal veto), while permitting spectator voting and read-only poll tallies.

## Problem Statement
The TypeScript `audience_studio` microservice provides high-concurrency chaos poll ingestion, vote tallying, and DM approval queues. However, the unified API Gateway currently has no routing or proxying configured for Audience Studio endpoints. Frontend clients and external streaming widgets cannot interact with audience polls through the single public entry point (`:8000`), and SpiceDB Zanzibar object authorization is not enforced at the gateway boundary.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/orchestrate-audience-chaos-polls.md`: Chaos poll lifecycles, spectator voting, and DM approval queues.
  - `docs/how-to/define-spicedb-zanzibar-permissions.md`: Fine-grained SpiceDB schema relations for spectator and campaign roles.
  - `docs/reference/ports-and-endpoints.md`: Gateway port 8000 and Audience Studio port 8010.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Fine-Grained Authorization**: Verify caller permissions against `runefoble.zed` for administrative and DM actions.
  - **ADR-0004: Unified API Gateway & Sub-Service Proxying**: Centralized ingress routing for microservices.
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event broadcasting and fanout.
  - **ADR-0007: Domain-Driven Design Architecture**: Strict service boundaries between gateway and backend context.

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0006-realtime-spectator-stream-and-chronicle.md`](../../user_stories/accepted/us-0006-realtime-spectator-stream-and-chronicle.md)
- [`us-0030-obs-transparent-party-vitals-and-multi-track-audio.md`](../../user_stories/accepted/us-0030-obs-transparent-party-vitals-and-multi-track-audio.md)
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)

## Detailed Specification & Implementation Plan
1. **FastAPI Audience Proxy Router (`gateway/api/src/gateway_api/routers/audience.py`)**:
   - Proxy routes to `AUDIENCE_STUDIO_URL` (default `http://localhost:8010` / `http://audience-studio:8010`):
     - `POST /api/v1/audience/polls` (Create poll; requires `can_manage_audience_polls` or `run_session`)
     - `GET /api/v1/audience/polls/{poll_id}` (Get poll tallies; public)
     - `POST /api/v1/audience/polls/{poll_id}/votes` (Submit spectator vote; public/spectator)
     - `POST /api/v1/audience/polls/{poll_id}/close` (Close poll; requires `can_manage_audience_polls`)
     - `GET /api/v1/audience/proposals` (List pending proposals; requires `can_approve_audience_chaos`)
     - `POST /api/v1/audience/proposals/{proposal_id}/approve` (Approve modifier; requires `can_approve_audience_chaos`)
     - `POST /api/v1/audience/proposals/{proposal_id}/veto` (Veto modifier; requires `can_approve_audience_chaos`)
   - WebSocket proxy:
     - `WS /ws/audience/{campaign_id}` proxying frames bidirectionally between client and audience studio.
2. **Mount in Gateway API (`gateway/api/src/gateway_api/main.py`)**:
   - Register `audience.router` under tags `["Audience"]`.
3. **Blackbox Tests (`tests/test_blackbox_gateway_audience_proxy.py`)**:
   - Assert all proxy routes, status forwarding, headers, and Zanzibar permission gating.

## INVEST Criteria Evaluation
- **Independent (I)**: Exposes public REST and WS edge routes independently of frontend component rendering.
- **Negotiable (N)**: Timeout thresholds and proxy connection pooling can be configured.
- **Valuable (V)**: Enables spectators and streaming overlays to interact with game sessions securely.
- **Estimable (E)**: Follows existing router proxy conventions established across the gateway.
- **Small (S)**: Single proxy router (< 180 lines) and one blackbox test suite.
- **Testable (T)**: Frontdoor HTTP and WebSocket test harness verifying status codes and permission denials.

## Definition of Done
1. `gateway/api/src/gateway_api/routers/audience.py` implemented with file length strictly < 200 lines.
2. Gateway routes `/api/v1/audience/*` forward to `audience-studio` and enforce Zanzibar permissions.
3. Frontdoor blackbox tests `tests/test_blackbox_gateway_audience_proxy.py` pass with 100% assertions using HTTP client.
4. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
