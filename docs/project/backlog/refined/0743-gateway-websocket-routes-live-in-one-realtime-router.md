---
id: '0743'
title: Gateway WebSocket Routes Live in One Realtime Router
status: Refined
created: 2026-11-17
dependencies:
- TASK-0488
- TASK-0544
- TASK-0592
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0005
governing_stories:
- US-0014
target_bc: gateway
target_release: 0.9.0
---
# TASK-0743: Gateway WebSocket Routes Live in One Realtime Router

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
The composition root defines six WebSocket handlers inline and imports `game_session` internals inside function bodies. The root holds endpoint logic.

## Problem Statement
- `gateway/api/src/gateway_api/main.py:131-191` defines `/ws/campaigns`, `/ws/session`, `/ws/voice`, `/ws/mobile-companion`, `/ws/establishments/.../tables/...`, and `/ws/minigames/...` inline. Two import `game_session.routers.minigames_ws` inside the function (`:178`, `:189`).
- `main.py:207-215` re-exports names through `__all__`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- TASK-0488 owns the double mount and the re-exports. TASK-0544 changes `/ws/session`. TASK-0592 replaces the minigame socket with a proxy. Run after all three, so the move is a pure move.

## Product & User Story References
- PRD-0005
- US-0014

## Detailed Specification & Implementation Plan
1. Move the remaining inline handlers into `gateway_api/routers/realtime.py` exposing one `APIRouter`. Include it once in `main.py`.
2. Do not change any path or close code.

## Frontdoor Blackbox Test Plan
- Connect to each WebSocket path through the gateway. Assert the `connected` frame and close codes. Assert the OpenAPI path list is equal before and after.

## Definition of Done
- `main.py` defines no `@app.websocket` handler and is under 120 lines.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: low
- Source audits: `gateway-api.md (F4)`
