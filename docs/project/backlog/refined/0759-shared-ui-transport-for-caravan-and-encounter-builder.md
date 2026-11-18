---
id: '0759'
title: Caravan and Encounter Builder Use the Shared UI Transport and Show Real Errors
status: Refined
created: 2026-11-17
dependencies:
- TASK-0758
governing_adrs:
- ADR-0013
- ADR-0015
governing_prds:
- PRD-0018
- PRD-0008
governing_stories:
- US-0062
target_bc: game_session
target_release: 0.9.0
---
# TASK-0759: Caravan and Encounter Builder Use the Shared UI Transport and Show Real Errors

## Status
Refined.

## Summary
Move the caravan, encounter builder and shell data client to the shared transport. The caravan client sends `x-user-id`, not a token, and maps every failure to "Authorization failed".

## Problem Statement
- `services/game_session/ui/src/caravan/caravan_api.ts:24` and `:53` send `x-user-id` and no Bearer token. Line 34 throws `err.detail || 'Authorization failed'`. A 503 without a detail shows an authorization message.
- `caravan_api.ts` holds two copies of the same POST logic (about lines 14-60).
- `services/rules_compendium/ui/src/runefoble-encounter-builder.ts:133` posts with no token.
- `frontend/src/services/app-data-service.ts:33-60` has a third `request()` with the same job.

## Documentation & Architecture Review
- ADR-0013, ADR-0015 (b). `docs/how-to/post-and-fulfill-mercenary-bounty-contracts.md` and `docs/how-to/balance-combat-encounters-and-query-compendium.md` need their error text corrected.
- Identity must come from the token, not a client-sent `x-user-id` (Invariant 1 spirit; see TASK-0538).

## Product & User Story References
- PRD-0018 (West Marches). PRD-0008 (compendium). US-0062.

## Detailed Specification & Implementation Plan
1. Replace both caravan POST copies with one call over `request`. Drop `x-user-id`.
2. `runefoble-encounter-builder.ts` uses `request`.
3. `app-data-service.ts` uses `request` and `HttpError`. Keep its `DataResult` shape for views.
4. Error text comes from `HttpError`: 401/403 say not authorized, 503 says service unavailable, other codes show the detail.

## Frontdoor Blackbox Test Plan
- Playwright BDD: post a caravan contract with a signed token. Assert the Bearer header and no `x-user-id`. Return 403 and 503 from a live loopback upstream and assert distinct messages.
- Encounter balance request carries the token.

## Definition of Done
- One transport in the repository for these three call sites. No fixed "Authorization failed" text.
- Docs corrected. Gates pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `frontend-ui`
