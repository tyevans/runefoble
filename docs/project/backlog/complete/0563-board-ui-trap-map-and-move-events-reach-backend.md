---
id: '0563'
title: Board UI Trap, Map Switch and Move Events Reach the Backend
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0013
- ADR-0006
governing_prds:
- PRD-0005
- PRD-0013
governing_stories:
- US-0018
- US-0014
target_release: 0.9.0
---

# TASK-0563: Board UI Trap, Map Switch and Move Events Reach the Backend

## Status
Complete

## Summary
Several board microfrontend events are dispatched but no listener calls the backend. The DM trap controls, map switcher, and token move send events that go nowhere, or go to the wrong socket message type. This task maps each UI event to its public HTTP route or WebSocket action, and checks the response in the owning component.

## Problem Statement
- `services/board_state/ui/src/runefoble-dm-trap-controls.ts` dispatches `trap-armed`, `trap-placed`, and `open-map-switcher`. `services/board_state/ui/src/runefoble-map-switcher.ts` (removed) dispatches `map-switched` (w1-board-state F9). No file in `frontend/src` or `services/*/ui/src` listens for these names.
- The component does not call `/api/v1/boards/*/traps` or `switch-map`.
- `frontend/src/runefoble-app.ts` sends `move-token` as `{type:'board_move'}` on the gateway session socket. The board service expects `{action:'confirm_move'}` on `/ws/boards/{id}`.
- `TASK-0388` (proposed) covers Playwright coverage of these components. It does not cover backend wiring.

## Documentation & Architecture Review
- ADR-0013: the component is vendored in `services/board_state/ui/`. The App Shell only composes it. The wiring must live in the owning component, not in `frontend/`.
- `docs/how-to/manage-secret-dm-traps-and-map-triggers.md` and `docs/how-to/interact-with-tactile-board-and-ghost-previews.md` describe these routes. Check them before coding and fix any mismatch.
- `docs/reference/ports-and-endpoints.md` lists the board routes.

## Product & User Story References
- [`prd-0003-spatial-fog-of-war-and-visibility-engine.md`](../../product/accepted/prd-0003-spatial-fog-of-war-and-visibility-engine.md) (board actions)
- [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
- [`us-0018-secret-dm-traps-map-switching-and-stage-triggers.md`](../../user_stories/accepted/us-0018-secret-dm-traps-map-switching-and-stage-triggers.md)

## Detailed Specification & Implementation Plan
1. In `runefoble-dm-trap-controls.ts`, on `trap-armed` and `trap-placed`, call `POST /api/v1/boards/{id}/traps` with the public payload. Show the server's response state, not an optimistic one.
2. In `runefoble-map-switcher.ts`, on selection, call the switch-map route and emit `map-switched` only after a 2xx response.
3. In the board component, map `move-token` to the WebSocket action `confirm_move` on `/ws/boards/{id}`. Remove the `board_move` payload. Set the board socket URL to the board service path, not the gateway session socket.
4. Document the event-to-route table in `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`.
5. Storybook: each component has a story that stubs `fetch` at the browser boundary and asserts the request body.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** in the browser (Playwright BDD, public UI only), the DM arms a trap in the sidebar. Then call `GET /api/v1/boards/{id}/traps` as the DM. Before: empty list. After: the trap is listed.
- **Fail before, pass after:** the DM switches map through the switcher. Then `GET /api/v1/boards/{id}` returns the new map id. Before: unchanged.
- **Fail before, pass after:** a token move in the UI produces a persisted position on the public board read route.
- No backdoor setup. Board creation uses the public route.

## Definition of Done
1. Each listed UI event produces a verified backend call. Storybook stories have zero console errors.
2. Three Playwright BDD scenarios above pass.
3. `pnpm run build` and `make build` pass. Changed files under 500 lines.
4. How-to updated with the event-to-route table. `CHANGELOG.md` entry.

## Audit Provenance

- Severity: high
- Source audits: `w1-board-state.md`
