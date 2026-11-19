---
id: '0867'
title: App Data Mappers Reject Missing Required Fields Instead of Inventing Them
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0013
- ADR-0015
governing_prds:
- PRD-0023
governing_stories:
- US-0068
target_bc: frontend
target_release: 0.9.0
---
# TASK-0867: App Data Mappers Reject Missing Required Fields Instead of Inventing Them

## Status
Refined.

## Summary
The App Shell data mappers replace missing values with defaults. A board with no size becomes a 10 by 10 board. A session with no status becomes `active`. Required fields must return a data failure. The shell must not show a guessed value.

## Problem Statement
- `frontend/src/services/app-data-service.ts:178`: `cols: res.data?.cols ?? 10, rows: res.data?.rows ?? 10`. A missing size is shown as a 10 by 10 grid.
- `frontend/src/services/app-data-service.ts:121-122`: `status: data.status || 'active'`, `round: data.round || 1`. A missing status is shown as active.
- `frontend/src/services/app-data-service.ts:120-124`: the session mapper also reads `campaign_id` or `campaignId`, and `participants` or `participantsCount`. This task does not change the wire casing. TASK-0771 owns that change.

## Documentation & Architecture Review
- ADR-0015 (no hidden failure, no substitute values).
- ADR-0013: the shell owns its view models. Read `docs/reference/microfrontend-architecture.md` before editing the shell data layer.
- TASK-0762 splits this same file. This task lands first (see TASK-0762 addendum in the index).

## Product & User Story References
- PRD-0023 (unified App Shell). US-0068 (App Shell view audit and API proxying).

## Detailed Specification & Implementation Plan
1. In each mapper in `app-data-service.ts`, list the required fields in one constant near the mapper.
2. When a required field is missing or has the wrong type, return the existing `dataFailure` shape with a clear message. Remove the `?? 10`, `|| 'active'`, `|| 1` and `|| ''` defaults for required fields.
3. Optional fields (for example `tokens`) keep an empty list. Document each optional field in a comment.
4. Update `frontend/src/fixtures/app-data-service.fixtures.ts` so that every fixture has the required fields.
5. Do not change wire casing in this task.

## Frontdoor Blackbox Test Plan
- Vitest unit tests in `frontend/test/` for each mapper: a payload with each required field removed returns a failure. A complete payload returns the same values as before.
- Playwright BDD (ADR-0014): a board read returns a body without `cols` and `rows` through a live loopback upstream. The shell shows the data error and no grid.
- Existing route tests `frontend/test/router.test.ts` and `frontend/test/app-shell-views-wiring-audit.test.ts` pass unchanged.

## Definition of Done
- No default value for a required field in `app-data-service.ts`.
- Unit tests and the BDD scenario pass.
- `pnpm run build` and `make lint` pass. No file over 500 lines.
- No backward-compatibility shim (DoR 9).

## Audit Provenance
- Severity: high
- Source audits: `frontend-ui`
