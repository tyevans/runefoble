---
id: '0812'
title: "Forge and Caravan UI Clients Send the Bearer Token"
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0013
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: asset_forge
target_release: 0.9.0
---

# TASK-0812: Forge and Caravan UI Clients Send the Bearer Token

## Status
Complete

## Summary
The asset forge UI client and the caravan UI client send no `Authorization` header, but the routes they call require one. The caravan client sends an `x-user-id` header that no backend reads.

## Problem Statement
- `services/asset_forge/ui/src/forge-api.ts:153-166` (`postForge`) and its callers.
- `services/game_session/ui/src/caravan/caravan_api.ts:18-58`: `x-user-id`, no bearer, calls gateway routes that do not exist yet (TASK-0807).
- `.audit/research/frontend-ui.md` F-01, F-02.

## Documentation & Architecture Review
- AGENTS.md Hard Invariant 1 (SpiceDB) and DoR 9.
- ADR-0001, ADR-0013, ADR-0015. `docs/how-to/verify-identity-in-fastapi-and-websockets.md`, `docs/how-to/define-spicedb-zanzibar-permissions.md`.

## Product & User Story References
None. Security defect.

## Detailed Specification & Implementation Plan
1. Send the bearer through the shared `libs/runefoble_ui` auth consumer (the same path `AssetImageController` uses). Delete `x-user-id`.
2. Show a typed error on 401 and 403.
3. Caravan calls stay behind TASK-0807 for the gateway routes; this task fixes the client headers only.

## Frontdoor Blackbox Test Plan
- Vitest browser tests: each forge call carries `Authorization: Bearer <token>`; a 401 shows the sign-in error.
- A Playwright BDD forge scenario passes against the gateway.

## Definition of Done
- The test plan passes, including with a live SpiceDB (`make test-authz-live`).
- `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high (authorization)
- Source audits: research reports in `.audit/research/` (verified by the orchestrator 2026-11-18)
