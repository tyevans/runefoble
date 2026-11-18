---
id: '0810'
title: "Session WebSocket Requires session.participate for Inbound Frames"
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

# TASK-0810: Session WebSocket Requires session.participate for Inbound Frames

## Status
Complete

## Summary
The gateway session WebSocket admits `session.observe` users and then rebroadcasts every frame they send to the whole session.

## Problem Statement
- `gateway/api/src/gateway_api/session_websocket.py:17-38`: admit with `session.observe`, then `manager.broadcast(session_id, data)` for every inbound frame.
- `gateway/api/src/gateway_api/routers/overlay.py:88-104` already requires `session.participate` for inbound frames. Two rules apply to one room.

## Documentation & Architecture Review
- AGENTS.md Hard Invariant 1 (SpiceDB) and DoR 9.
- ADR-0001, ADR-0015. `docs/how-to/verify-identity-in-fastapi-and-websockets.md`, `docs/how-to/define-spicedb-zanzibar-permissions.md`.

## Product & User Story References
None. Security defect.

## Detailed Specification & Implementation Plan
1. Observers may receive but not send. An inbound frame from a caller without `session.participate` gets an error frame and is not rebroadcast.
2. Validate inbound frames with a Pydantic model. Unknown frame types get an error frame.
3. Use one inbound rule for the session and overlay sockets (one shared helper).

## Frontdoor Blackbox Test Plan
- An observer sends a frame. It receives an error frame, and a second participant socket receives nothing.
- A participant sends a frame. The other sockets receive it.

## Definition of Done
- The test plan passes, including with a live SpiceDB (`make test-authz-live`).
- `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high (authorization)
- Source audits: `.audit/research/gateways.md` (urgent items, verified by the orchestrator 2026-11-18)
