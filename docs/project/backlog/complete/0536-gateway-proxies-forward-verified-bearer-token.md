---
id: '0536'
title: Gateway Proxies Forward the Verified Bearer Token to Services and Return Honest Errors
status: Complete
created: 2026-11-17
dependencies:
- TASK-0521
governing_adrs:
- ADR-0005
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0013
target_release: 0.9.0
---

# TASK-0536: Gateway Proxies Forward the Verified Bearer Token to Services and Return Honest Errors

## Status
Complete

## Summary
Services now verify the caller's token themselves (TASK-0527 to TASK-0531). The gateway's proxies must forward the bearer token, not a user header. Today the proxies send no identity, so every proxied call looks anonymous. Also, a proxy error must return the upstream status, not a success with the wrong data. Canned fallback removal belongs to the fake-implementation theme; this task changes identity and error status only.

## Problem Statement
- `gateway/api/src/gateway_api/routers/hub_views.py:16-25` (`_proxy_or_fallback`) sends no headers. Audit w2-campaign-lore F14 and w2-campaign-analytics F7.
- `gateway/api/src/gateway_api/routers/character_subresources.py:26,36-48` proxies to `CHARACTER_SHEET_URL`, which is unset in Helm. On any proxy error it uses in-memory state and forwards no identity. Audit w3-authz F20 (ingress and reachability).
- `gateway/api/src/gateway_api/routers/soundscape.py` falls back to in-process imports when `SOUNDSCAPE_SERVICE_URL` is missing. The in-process path bypasses service verification.
- The gateway has no single proxy helper. Each router builds its own request.

## Documentation & Architecture Review
- Single proxy helper in `gateway/api/src/gateway_api/proxy.py` (new). It forwards `Authorization` and nothing else for identity. It never forwards `X-User-Id`.
- Upstream 401 and 403 pass through unchanged. Connection failure and upstream 5xx return 502 with a fixed message.
- Canned fallback payloads are removed by the fake-implementation theme (audit w2-campaign-lore F14). This task must not add new fallbacks.
- Services that the gateway imports in process (`voice_agent`, `game_session`) are a DDD issue (audit w1-gateway-api). Out of scope.

## Product & User Story References
- PRD-0023 (App Shell reads through the gateway). US-0013.

## Detailed Specification & Implementation Plan
1. Create `gateway/api/src/gateway_api/proxy.py` with one function that takes the request, the target base URL, and the path. It copies the `Authorization` header and no other identity header.
2. Route `hub_views.py` campaign-analytics and campaign-lore calls through the helper. Remove `_proxy_or_fallback` canned payloads in this file only if the fake-implementation theme has not already done so; otherwise leave them and record it in the PR.
3. Route `character_subresources.py` through the helper. The target is `CHARACTER_SHEET_URL`. Set that variable in Helm (TASK-0624 owns the Helm wiring for service URLs).
4. Route `soundscape.py` through the helper. Remove the in-process identity bypass for requests that carry a bearer token.
5. Return 502 when the upstream is unreachable. Pass upstream 4xx through.
6. Document the forwarding rule in `docs/reference/ports-and-endpoints.md` (TASK-0537 consolidates the identity reference).

## Frontdoor Blackbox Test Plan
HTTP tests through the gateway, with a stub upstream that echoes the headers it receives.
- Before: a proxied request arrives at the stub with no `Authorization` header. An upstream connection error returns the canned payload with 200.
- After:
  - The stub receives the same `Authorization` value the client sent.
  - The stub receives no `X-User-Id` header from the gateway.
  - An upstream 403 reaches the client as 403.
  - An unreachable upstream returns 502.

## Definition of Done
1. `grep -rn "X-User-Id\|x-user-id" gateway/api/src/gateway_api/proxy.py routers/hub_views.py routers/character_subresources.py routers/soundscape.py` returns no matches.
2. Gateway proxy test passes.
3. Existing hub and soundscape suites pass or are updated to the 502 contract.
4. No file exceeds 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w2-campaign-lore.md`, `w2-campaign-analytics.md`, `w1-gateway-api.md`, `w3-authz-coverage.md`
