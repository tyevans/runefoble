---
id: '0807'
title: "Gateway Proxies Shared-World Caravan Routes and the App Shell Mounts the Caravan Board"
status: Refined
created: 2026-11-18
dependencies:
- TASK-0685
governing_adrs:
- ADR-0004
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds:
- PRD-0018
governing_stories:
- US-0058
target_bc: game_session
target_release: 0.9.0
---

# TASK-0807: Gateway Proxies Shared-World Caravan Routes and the App Shell Mounts the Caravan Board

## Status
Refined. Split from TASK-0685 (blocked item 1b), 2026-11-18.

## Summary
The caravan board cannot mount in the App Shell, because the gateway has no proxy for the shared-world caravan routes that game_session owns.

## Problem Statement
- `gateway/api/src/gateway_api/` has no route for `/api/v1/shared-worlds/...`.
- game_session owns the routes in `services/game_session/src/game_session/routers/caravan_contracts/` (list contracts, accept, dispatch, fulfill).
- `e2e/features/caravan_board.feature` keeps its `@blocked` tag.

## Documentation & Architecture Review
- `docs/how-to/call-owning-services-through-the-gateway.md`, `docs/how-to/coordinate-west-marches-shared-world-and-caravans.md`.
- ADR-0015 b: the gateway stays thin (`forward_json` through ServiceClient).

## Product & User Story References
PRD-0018, US-0058.

## Detailed Specification & Implementation Plan
1. Add a thin gateway router that forwards the shared-world caravan routes to game_session with the caller bearer. No business logic in the gateway.
2. Add an App Shell route and view that mounts the vendored caravan board component with the shared-world id.
3. Remove `@blocked` from `e2e/features/caravan_board.feature`.

## Frontdoor Blackbox Test Plan
- Gateway tests against a live loopback game_session: each forwarded route returns the owner status and body; a caller without access gets the owner 403.
- App Shell test that the route mounts the board with the shared-world id.
- The caravan Playwright BDD scenarios pass.

## Definition of Done
- The test plan passes.
- `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0685.md` (Blocker)
