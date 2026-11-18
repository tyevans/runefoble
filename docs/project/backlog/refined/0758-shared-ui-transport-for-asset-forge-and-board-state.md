---
id: '0758'
title: Shared UI Transport Client Replaces Per-Package Fetch Code in Forge and Board
status: Refined
created: 2026-11-17
dependencies:
- TASK-0757
governing_adrs:
- ADR-0013
- ADR-0015
governing_prds:
- PRD-0023
governing_stories:
- US-0062
target_bc: frontend
target_release: 0.9.0
---
# TASK-0758: Shared UI Transport Client Replaces Per-Package Fetch Code in Forge and Board

## Status
Refined.

## Summary
Each microfrontend has its own `postJson`, error class and error text reader. Add one `request<T>()` and one `HttpError` to `libs/runefoble_ui` (created in TASK-0757). Move `asset_forge` and `board_state` to it. TASK-0759 moves the rest.

## Problem Statement
- `services/asset_forge/ui/src/forge-api.ts:94` (`ForgeApiError`), `:130` (`readErrorMessage`), `:153` (`postForge`).
- `services/board_state/ui/src/board-api.ts:9` (`BoardApiError`), `:70` (`readFailureDetail`), `:81` (`postJson`).
- `services/board_state/ui/src/physics_3d/physics_bridge.ts:83` and `:100` use the literal `/api/v1/boards/...` path and no token.
- `services/board_state/ui/src/runefoble-map-dropzone.ts:60` posts a `FormData` upload with no token.

## Documentation & Architecture Review
- ADR-0013 (package vendoring), ADR-0015 (b) (errors are visible).
- `docs/reference/service-client.md` covers the Python gateway client. Add `docs/reference/ui-transport.md` for the TypeScript client.
- Overlap: TASK-0538 covers "send the token on every call" for the shell. This task builds the shared client. Do not duplicate: where 0538 has already changed a call, only swap the client.

## Product & User Story References
- PRD-0023. US-0062.

## Detailed Specification & Implementation Plan
1. In `libs/runefoble_ui`: `request<T>(path, init)` with the token from the TASK-0757 controller, an API base setting, JSON and `FormData` bodies, and `HttpError { status, detail }` that reads the FastAPI `detail`.
2. `forge-api.ts` and `board-api.ts` become thin typed calls over `request`. Delete `ForgeApiError`, `BoardApiError` and the local readers.
3. `physics_bridge.ts` and `runefoble-map-dropzone.ts` use the client and the API base.
4. Each caller renders `HttpError.detail`. Keep status-specific text only where the UI needs it (403, 503).

## Frontdoor Blackbox Test Plan
- Playwright BDD for forge and board: assert request URL, `Authorization` header, and the rendered error text for a 403 and a 503 from a live loopback upstream.
- Unit tests of `request` run against a real local HTTP server, not a patched `fetch`.

## Definition of Done
- No duplicate error class or reader remains in `asset_forge/ui` or `board_state/ui`.
- Reference doc added. Builds and gates pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `frontend-ui`
