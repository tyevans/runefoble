---
id: '0776'
title: WebSocket Admission Uses One Shared Helper
status: Refined
created: 2026-11-17
dependencies:
- TASK-0593
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---

# TASK-0776: WebSocket Admission Uses One Shared Helper

## Status
Refined. Refactor pause, 2026-11-17.

## Summary
Five tasks (0770, 0544, 0547, 0548, 0593) each wrote their own WebSocket connect check and close-code handling. The codes drifted (1008, 4003, 4403) until the orchestrator set one standard. Agreed at the refactor pause on 2026-11-17 (candidate 3).

## Problem Statement
- Separate admission code in the gateway session socket, realtime sockets, board socket, minigame sockets and voice_agent sockets.
- Close codes: 1008 means a missing or invalid token, 4403 means an authorization refusal (`docs/reference/ports-and-endpoints.md`).

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0001, ADR-0015.

## Product & User Story References
None. Architecture quality.

## Detailed Specification & Implementation Plan
1. Add one helper in `libs/runefoble_auth` (for example `admit_socket(websocket, resource_type, resource_id, permission) -> VerifiedPrincipal`) that verifies the bearer subprotocol, checks the schema permission, and closes with 1008 or 4403.
2. Add one helper for per-message checks with the same error frame shape (`PERMISSION_DENIED`, `UNKNOWN_ACTION`).
3. Move every socket to the helpers. Delete the copies.
4. Document the helper in `docs/how-to/verify-identity-in-fastapi-and-websockets.md`.

## Frontdoor Blackbox Test Plan
- For each socket: no token closes 1008; a user without the permission closes 4403; a permitted user connects. Run the same parametrised frontdoor test over every socket route.

## Definition of Done
- Every WebSocket admits callers through the shared helper. No socket has its own copy.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `drafts/round3-notes.md`
