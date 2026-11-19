---
id: '0762'
title: App Shell Owns Its View Models and Splits the Data Service by Bounded Context
status: Refined
created: 2026-11-17
dependencies:
- TASK-0648
- TASK-0759
governing_adrs:
- ADR-0013
- ADR-0007
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0064
target_bc: frontend
target_release: 0.9.0
---
# TASK-0762: App Shell Owns Its View Models and Splits the Data Service by Bounded Context

## Status
Refined.

## Summary
The shell imports data types from service UI packages, and one 223-line class holds about 43 methods of several contexts. Give the shell its own view-model types. Split the class by bounded context.

## Problem Statement
- `frontend/src/services/app-data-service.ts:3-6` imports `CharacterItem`, `CampaignItem`, `BoardToken`, `WatcherFeedEvent` from service packages.
- The same file mixes campaigns, characters, profile, invites and board state.
- Other type importers: `frontend/src/services/campaign-hub-client.ts`, `frontend/src/services/lobby-character-options.ts`, `frontend/src/utils/dice.ts`, `frontend/src/fixtures/app-data-service.fixtures.ts`.
- Not changed: `frontend/src/app/component-registry.ts:15-22` imports service packages for element registration. ADR-0013 point 4 allows this (`workspace:*`). Only types leave.

## Documentation & Architecture Review
- ADR-0013, ADR-0007 (bounded contexts). TASK-0648 removes orphaned imports and edits the same files. Do this after it.

## Product & User Story References
- PRD-0023. US-0063, US-0064.

## Detailed Specification & Implementation Plan
1. Add `frontend/src/models/` with view-model types for only the fields the shell shows.
2. Split `app-data-service.ts` into `campaign-data.ts`, `character-data.ts`, `profile-data.ts`, `board-data.ts` over the transport from TASK-0759. No re-export of the old class (DoR 9). Update all call sites.
3. Remove the type imports from service packages in the five files above.

Refactor round 2 addendum (2026-11-18): Depends on TASK-0867 (required-field mappers land first). The file now has 223 lines and about 43 methods. The text above says 212 lines and about 22 methods. Update the counts.

## Frontdoor Blackbox Test Plan
- Existing route tests `frontend/test/router.test.ts` and `frontend/test/app-shell-views-wiring-audit.test.ts` pass.
- Playwright BDD: one journey per route (campaigns, characters, profile, board). Assert that each route renders.

## Definition of Done
- No service type import in shell data code. No data file over 150 lines.
- Gates pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `frontend-ui`
