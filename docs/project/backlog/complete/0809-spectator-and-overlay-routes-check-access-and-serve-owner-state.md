---
id: '0809'
title: "Spectator and Overlay Routes Check Session Access and Serve Owner State"
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: gateway_api
target_release: 0.9.0
---

# TASK-0809: Spectator and Overlay Routes Check Session Access and Serve Owner State

## Status
Complete

## Summary
The spectator and overlay HTTP routes make no permission check, and they serve a fixture state (with DM-only fields) for every session that is not in a gateway memory store.

## Problem Statement
- `gateway/api/src/gateway_api/routers/spectator.py:19-64`: no `has_session_permission` check. A query `token` is not verified and becomes the viewer id. The GET publishes an event.
- `gateway/api/src/gateway_api/routers/overlay.py:64-86`: no check. The overlay WebSocket checks `session.observe`; the HTTP route does not.
- `gateway/api/src/gateway_api/spectator.py:65-180`: `_RAW_SESSION_STORE` and `get_default_raw_state` (fixture with "Valeros") serve as live data. Tests set state through module setters.

## Documentation & Architecture Review
- AGENTS.md Hard Invariant 1 (SpiceDB) and DoR 9.
- ADR-0001, ADR-0015. `docs/how-to/verify-identity-in-fastapi-and-websockets.md`, `docs/how-to/define-spicedb-zanzibar-permissions.md`.

## Product & User Story References
None. Security defect.

## Detailed Specification & Implementation Plan
1. Both HTTP routes require `session.observe` (SpiceDB) for a signed-in viewer. A spectator access token, if kept, goes in a header and is verified by its owner; otherwise remove the anonymous path.
2. Read the session state from its owner (game_session and board_state) through ServiceClient. Delete the gateway memory store, the fixture default and the setters (ADR-0015 b).
3. The GET has no side effect. Move the connection event to the WebSocket admit, or delete it.
4. Rewrite the tests through the frontdoor with live loopback owners.

## Frontdoor Blackbox Test Plan
- A viewer without `session.observe` gets 403 from both routes.
- An unknown session gives 404 from the owner, not fixture data.
- No DM-only field appears in either response.

## Definition of Done
- The test plan passes, including with a live SpiceDB (`make test-authz-live`).
- `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high (authorization)
- Source audits: `.audit/research/gateways.md` (urgent items, verified by the orchestrator 2026-11-18)
