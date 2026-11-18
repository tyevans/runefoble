---
id: '0723'
title: Audience Studio WebSocket Does Not Leak Internal Errors
status: Refined
created: 2026-11-17
dependencies:
- TASK-0499
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0011
governing_stories: []
target_bc: audience_studio
target_release: 0.9.0
---
# TASK-0723: Audience Studio WebSocket Does Not Leak Internal Errors

## Status
Refined. Found by the refactor audit round r1 and checked against the code by the orchestrator.

## Summary
The audience WebSocket sends the raw text of any thrown error to the client. Unknown actions get no reply. The manager mixes registry, command dispatch, mapping and broadcast.

## Problem Statement
- `services/audience_studio/src/websocket.ts:83`: `this.send(socket, { type: 'error', message: errorMsg })` sends internal text (for example SpiceDB or Redis errors).
- `websocket.ts:92-125`: `handleMessage` is an if-chain on `msg.action` with no `else`. Unknown actions are dropped.
- `websocket.ts:152,167`: magic `readyState === 1`. `websocket.ts:172-179`: `getClientCount` has no caller.
- `ws` is imported (`websocket.ts:10`) but is not a direct dependency in `package.json`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
- PRD-0011

## Detailed Specification & Implementation Plan
1. Send a typed error frame with a fixed code (`invalid_message`, `unknown_action`, `internal_error`). Log the real error on the server.
2. Replace the if-chain with a `Map<action, handler>` in `ws/commandDispatcher.ts`. Reply `unknown_action` for others.
3. Move authorization and fan-out into `ws/broadcaster.ts`. Use `WebSocket.OPEN`. Delete `getClientCount`.
4. Add `ws` to `package.json` dependencies.
5. Sequence after TASK-0499. Coordinate with TASK-0455 and 0456, which add ingestion paths.

## Frontdoor Blackbox Test Plan
- Send an unknown action: the client receives `unknown_action`.
- Make the store throw: the client receives `internal_error` with no internal text.
- `test/authorization_ws.test.ts` and `test/identity_ws.test.ts` pass.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r1/audience-scripts-helm.md`
