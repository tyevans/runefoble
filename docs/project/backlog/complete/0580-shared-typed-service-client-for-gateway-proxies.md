---
id: '0580'
title: Shared Typed Service Client for Gateway Proxies
status: Complete
created: 2026-11-17
dependencies:
- TASK-0624
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0023
governing_stories:
- US-0013
target_release: 0.9.0
---

# TASK-0580: Shared Typed Service Client for Gateway Proxies

## Status
Complete

## Summary
Add one typed HTTP client for calls from a gateway to an owning bounded context. The client lives in `libs/runefoble_platform`. It sets the timeout for each call, injects trace headers, forwards the verified caller identity, and maps upstream failures to HTTP 502 or 503. It has no fallback. Later router tasks (TASK-0581 to TASK-0596) use this client and delete their own canned or in-process code.

## Problem Statement
- Nine hand-rolled `httpx.AsyncClient` calls exist, with timeouts of 1.5, 2.0, 5.0 and 10.0 seconds. There is no shared retry, trace or identity policy (`w3-ddd-architecture.md` F17).
- Three of these calls use silent fallback wrappers. Examples: `gateway/api/src/gateway_api/routers/hub_views.py:16-24` (removed), `routers/soundscape.py:24-37`, `routers/character_subresources.py:29-48`. Each one has `except Exception: pass` (`w1-gateway-api.md` F13, `w3-ddd-architecture.md` F18).
- No proxy forwards the caller identity. `hub_views.py:18` sends no headers, so campaign-lore treats every gateway call as anonymous (`w2-campaign-lore.md` F14).
- `libs/runefoble_platform` has no service client. Its `httpx` users are storage, analytics and email (`storage.py`, `analytics/client.py`, `email/mailpit.py`). None of them is a service-to-service client.

## Documentation & Architecture Review
- Read: `AGENTS.md` (invariants 2, 5, 6; DoR 9 forbids fallbacks and shims), `docs/reference/architecture-overview.md` (gateway owns routing, not domain logic), `docs/reference/ports-and-endpoints.md`, `docs/project/adrs/accepted/adr-0007-domain-driven-design-architecture.md`.
- `libs/runefoble_platform/src/runefoble_platform/telemetry.py` already sets up OpenTelemetry. Reuse its propagator. Do not add a second tracing setup.
- Base URLs come from `PlatformSettings`. TASK-0624 defines the Helm variable names. This task reads those names. It adds no code default that points at `localhost` or a wrong port.
- Governing decision: a downstream failure is an error, not data. Return the upstream status, or 502 or 503. Never return a canned body.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0013-gateway-zanzibar-authorization.md`](../../user_stories/accepted/us-0013-gateway-zanzibar-authorization.md)

## Detailed Specification & Implementation Plan
1. Create package `libs/runefoble_platform/src/runefoble_platform/service_client/` with three modules, each under 150 lines:
   - `client.py`: class `ServiceClient(service: str, base_url: str, transport: httpx.AsyncBaseTransport | None = None)`.
     - Method `async send(method, path, *, principal_id: str | None, json=None, params=None, timeout_s: float) -> UpstreamReply`.
     - `UpstreamReply` is a dataclass with `status_code: int`, `content_type: str`, `body: bytes`.
     - One `httpx.AsyncClient` per instance. Add `async aclose()`.
     - Public `transport` argument for tests. Do not monkeypatch.
   - `errors.py`: `UpstreamUnavailableError` (connect failure or timeout, service name attached), `UpstreamFailureError` (upstream status 5xx, status and body attached). Upstream 2xx and 4xx pass through as `UpstreamReply`.
   - `headers.py`: builds outgoing headers. It injects W3C `traceparent` from the active span. It sets the principal header only from `principal_id`. It never copies client headers. The header name comes from the constant that `runefoble_auth` exports. The authorization theme owns that contract.
2. Gateway wiring (`gateway/api/src/gateway_api/upstream_errors.py`, new): register exception handlers in `main.py`. `UpstreamUnavailableError` becomes HTTP 503. `UpstreamFailureError` becomes HTTP 502. The body is `{"detail": "...", "upstream": "<service>"}`. Log each error at warning level.
3. Settings: add gateway upstream URL fields to `PlatformSettings` in `libs/runefoble_platform/src/runefoble_platform/config.py`. Use aliases `RUNEFOBLE_<SERVICE>_URL`, the names TASK-0624 renders. Initial set: `GAME_SESSION`, `BOARD_STATE`, `THE_WATCHER`, `CHARACTER_SHEET`, `CAMPAIGN_LORE`, `CAMPAIGN_ANALYTICS`, `SOUNDSCAPE`, `RULES_COMPENDIUM`, `ASSET_FORGE`, `VOICE_AGENT`, `AUDIENCE_STUDIO`. Required when the gateway starts outside test mode.
4. Create the client once in the FastAPI lifespan in `gateway/api/src/gateway_api/main.py`. Store it on `app.state`. Close it on shutdown. Expose a FastAPI dependency in `gateway/api/src/gateway_api/dependencies.py`.
5. Do not add retries. Do not add caching.
6. Docs (generic pattern, DoD item 4):
   - Create `docs/reference/service-client.md` (reference: constructor, `send`, errors, headers, status mapping).
   - Create `docs/how-to/call-owning-services-through-the-gateway.md` (how to add a proxy route).

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_service_client.py`. The upstream is a real FastAPI app, passed through `httpx.ASGITransport`. The test uses only public constructor arguments and public HTTP on the gateway.

| Case | Setup | Expected |
|---|---|---|
| Upstream 404 passes through | Upstream route returns 404 with JSON body | Gateway returns 404 and the same body |
| Upstream 500 becomes 502 | Upstream raises 500 | Gateway returns 502 with `upstream` set |
| Upstream unreachable becomes 503 | Transport raises `ConnectError` | Gateway returns 503 within `timeout_s` |
| Principal forwarded, client headers not | Gateway request carries `X-Forwarded-Foo` and a verified principal | Upstream sees the principal header and not `X-Forwarded-Foo` |
| Trace header injected | Active span in the test | Upstream sees `traceparent` |

Before the change the module does not exist, so every case fails. After the change all cases pass.

## Definition of Done
1. Package `service_client` exists. Each module is under 150 lines.
2. `rg "httpx.AsyncClient" services gateway` returns no service-call sites outside `service_client` (the storage, analytics and email clients are exempt).
3. Gateway maps upstream failures to 502 and 503. There is no `except Exception: pass` in the proxy path.
4. Settings expose the upstream URL fields. `rg "os.getenv|os.environ" gateway/api/src` returns no service URL reads.
5. Docs in `docs/reference/service-client.md` and `docs/how-to/call-owning-services-through-the-gateway.md` exist and match the code.
6. `uv run pytest tests/test_blackbox_service_client.py` passes. `uv run ruff check .` passes.

## Audit Provenance

- Severity: high
- Source audits: `w3-ddd-architecture.md`, `w1-gateway-api.md`, `w1-gates-infra.md`
