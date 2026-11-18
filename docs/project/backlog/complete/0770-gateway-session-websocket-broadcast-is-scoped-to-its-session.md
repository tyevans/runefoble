---
id: '0770'
title: Gateway Session WebSocket Broadcast Is Scoped to Its Session
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0013
governing_prds: []
governing_stories: []
target_bc: gateway
target_release: 0.9.0
---

# TASK-0770: Gateway Session WebSocket Broadcast Is Scoped to Its Session

## Status
Complete

## Summary
The gateway session WebSocket keeps one flat list of sockets and sends every message to all of
them. A message in one session (token moves, AoE templates, DM actions) reaches every connected
client of every other session. This leaks game state across tables, including content a DM may
want hidden.

## Problem Statement
- `gateway/api/src/gateway_api/dependencies.py:21-40`: `WebSocketConnectionManager` has one
  `active_connections` list. `broadcast(message)` sends to every socket.
- `gateway/api/src/gateway_api/main.py` `session_websocket`: the route takes `session_id` but does
  not use it to group sockets.

## Documentation & Architecture Review
- ADR-0001: a client receives only what `session.observe` allows.
- `docs/explanation/realtime-voice-and-board-sync.md`.

## Product & User Story References
None. Security and correctness.

## Detailed Specification & Implementation Plan
1. Group sockets by `session_id`. `broadcast(session_id, message)` sends only to that group.
2. Check `session.observe` for the verified caller when the socket connects. Refuse with close code
   4403 otherwise.
3. Keep the TASK fixmain16b behaviour: a failed send drops that socket and is logged.
4. If more than one gateway replica runs, fan out through the Redis bus per session (document the
   current single-replica limit if not done here).

## Frontdoor Blackbox Test Plan
- Two sessions, one client each. A message in session A reaches the A client. The B client gets no
  frame (assert with a receive time-out).
- A user with no relation to the session cannot connect (close 4403).

## Definition of Done
- No gateway WebSocket message crosses a session boundary.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `work/fixmain16b.md`
