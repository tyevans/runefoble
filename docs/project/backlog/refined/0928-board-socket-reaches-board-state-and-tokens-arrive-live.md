---
id: '0928'
title: "The Board Socket Reaches board_state, and Placed Tokens Arrive Live"
status: Refined
created: 2026-11-19
dependencies:
- '0922'
governing_adrs:
- ADR-0005
- ADR-0013
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: board_state
target_release: 0.9.0
---

# TASK-0928: The Board Socket Reaches board_state, and Placed Tokens Arrive Live

## Status

Refined.

## Summary

The ingress sends every `/ws` path to gateway-api. gateway-api has no `/ws/boards/{id}` route, so Starlette answers 403 and the live board socket never connects on Kind. Also, the gateway sends `board_ready` when the board is created, before the DM's client places the party tokens, so the player browsers read an empty board and never read it again.

## Problem Statement

- `deployments/helm/runefoble/values.yaml:64-66` and `:102-104`: `path: /ws` -> `gateway-api`.
- `services/board_state/src/board_state/routers/previews_ws.py:115`: `/ws/boards/{session_id}` is served by board_state, which admits the bearer and checks `board.view`.
- Gateway log on Kind: `WebSocket /ws/boards/<id> 403` twice; `POST /api/v1/boards 200`, then player `GET /api/v1/boards/<id> 200`, then `POST .../tokens 200` (the reads come before the tokens).
- `frontend/src/runefoble-app.ts:190` and `services/board_state/ui/src/board-api.ts:82` connect to `/ws/boards/{id}`.

## Documentation & Architecture Review

- `docs/reference/ports-and-endpoints.md` (ingress routing table), `deployments/helm/runefoble/values.yaml` (ingress paths).
- ADR-0005 (Kind and Helm), ADR-0015 (failures are visible).

## Product & User Story References

- `e2e/features/session_lobby_and_vtt.feature` scenarios 3 and 4.

## Detailed Specification & Implementation Plan

1. Add an ingress path `/ws/boards` -> `board-state` (more specific than `/ws`) in both ingress host blocks. Confirm the Traefik rule order puts the longer prefix first. Update the ingress routing table in `docs/reference/ports-and-endpoints.md`.
2. Check that a token placed through `POST /api/v1/boards/{id}/tokens` is broadcast on `board_ws_manager` to open board sockets. If not, broadcast it after the save.
3. Send `board_ready` only after the set-up has placed the party tokens: either the UI calls one gateway set-up route that creates the board and places the tokens, then broadcasts once, or the gateway token place route does not exist for set-up and the set-up route does both. Pick the simpler design and record it.

## Frontdoor Blackbox Test Plan

- Helm template test: the `/ws/boards` path routes to `board-state`.
- Blackbox: a client on the board socket receives a placed token frame after `POST .../tokens`.
- Blackbox: after a DM set-up through the gateway, each session socket gets one `board_ready`, and a board read after it returns the party tokens.
- Playwright on Kind (orchestrator): `session_lobby_and_vtt.feature` scenarios 3 and 4.

## Definition of Done

- Tests pass. Docs and CHANGELOG `Fixed` entry. The orchestrator runs the named Playwright scenarios on Kind.

## Audit Provenance

- Severity: high
- Source audits: .audit/work/e2e_full3.log
