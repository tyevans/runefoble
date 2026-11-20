---
id: '0936'
title: The Service Client Recovers From Stale Pooled Connections After an Owner Restart
status: Complete
created: 2026-11-19
dependencies:
- '0934'
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---

# TASK-0936: The Service Client Recovers From Stale Pooled Connections After an Owner Restart

## Status

Complete

## Summary

After game_session restarted, the gateway reused pooled keep-alive connections to the old pod. The next requests failed with `RemoteProtocolError` and the gateway answered 503, although the new pod was ready. Any owner restart (rollout, crash, scale) gives the same failure for the first requests on each pooled connection.

## Problem Statement

- Gateway log: `Upstream game_session unavailable: RemoteProtocolError` -> `GET /api/v1/campaigns 503` and `GET /api/v1/campaigns/{id} 503`, right after the caravan @game-session-down scenario scaled game-session back to 1.
- e2e "Marking Absentee AI Stand-In" then showed "Upstream service is unavailable".
- `libs/runefoble_platform/src/runefoble_platform/service_client/`: one pooled `httpx.AsyncClient` per owner; no retry on a dropped pooled connection; the client keep-alive expiry may race the server keep-alive timeout (uvicorn default 5 s, httpx default 5 s).

## Documentation & Architecture Review

- `docs/reference/service-client.md` (errors and gateway status mapping).
- ADR-0015: an outage is reported, never hidden; a dropped stale connection to a healthy owner is not an outage.

## Product & User Story References

None. Reliability after any restart.

## Detailed Specification & Implementation Plan

1. On `httpx.RemoteProtocolError` (or a pooled-connection close before any response) the client retries once on a fresh connection for idempotent methods (GET, HEAD, PUT, DELETE, OPTIONS). Non-idempotent methods (POST, PATCH) are not retried blindly; they map to 503 as today, unless the request carries an idempotency key that the owner honours (document which routes do).
2. Set the client keep-alive expiry below the server keep-alive timeout, and set the services' uvicorn `--timeout-keep-alive` explicitly in the images, so the race is removed by configuration, not by luck.
3. Log one warning per retried request with the owner and method.
4. Document the rule in `docs/reference/service-client.md`.

## Frontdoor Blackbox Test Plan

- A live loopback owner that closes a pooled connection after the first reply: a second GET through the gateway succeeds (retried once), a second POST answers 503.
- An owner that is down: still 503 within the connect limit (TASK-0934).
- Orchestrator on Kind: the full e2e suite twice in a row with the @game-session-down scenarios in the middle; no scenario after them fails with 503.

## Definition of Done

- Tests pass. Docs and CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: high
- Source audits: .audit/work/e2e_full9.log
