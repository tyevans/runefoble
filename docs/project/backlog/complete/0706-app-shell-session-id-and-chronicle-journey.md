---
id: '0706'
title: One Session Id From Campaign Session to Game Session Aggregate
status: Complete
created: 2026-11-17
dependencies:
- TASK-0695
governing_adrs:
- ADR-0011
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds:
- PRD-0023
governing_stories:
- US-0065
target_bc: game_session
target_release: 0.9.0
---
# TASK-0706: One Session Id From Campaign Session to Game Session Aggregate

## Status
Complete

Review 2026-11-18: rescoped to the id model. Decision (orchestrator): one id per session, option A of `.audit/work/0706.md`. The e2e web server set and the chronicle journey moved to TASK-0842.

## Summary
A campaign session has the id `session-<hex>` (`services/game_session/src/game_session/campaign/service_campaigns.py`, lines 132 and 217). The `GameSession` aggregate has a UUID id, and only `POST /api/v1/sessions/create` makes one. The App Shell holds the campaign session id, and the session read, start and combat routes refuse it. One session must have one id.

## Problem Statement
The App Shell cannot read, start or run combat in the session it launched. Two id models for one thing break `docs/reference/identifiers-and-uuid-policy.md`.

## Documentation & Architecture Review
- `docs/reference/identifiers-and-uuid-policy.md` (ADR-0015): no second id model, no random substitute ids.
- `docs/how-to/coordinate-game-session-lobby-and-readiness.md`, `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md`.
- `docs/reference/game-session-child-indexes.md`: the campaign session list links child aggregates.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)

## Detailed Specification & Implementation Plan
1. `POST /api/v1/campaigns/{id}/sessions` creates the `GameSession` aggregate in the same call, with a new UUID. The campaign session entry stores that UUID as its id. The same applies to the seeded first session (line 132). The `session-` prefix goes.
2. The campaign session response and list return that UUID. The session read, start, combat and turn routes accept it.
3. The App Shell launch and the session view use that id. No second id is stored in the client.
4. Update every test and e2e helper that builds or asserts a `session-` id.
5. Update the docs above.

## Frontdoor Blackbox Test Plan
- Create a campaign session through the public route. `GET /api/v1/sessions/{id}` with the returned id answers 200. Start the session, start combat and advance a turn with the same id.
- The campaign session list shows the same id.
- Through the gateway: the same flow answers 200 for the DM.

## INVEST Criteria Evaluation
Independent of TASK-0842. Small: one create path, call sites and tests. Testable through public routes.

## Definition of Done
1. The test plan passes. 2. No code builds a `session-` id. 3. Docs are current. 4. `make health-check` passes.

## Audit Provenance
- Severity: medium
- Source audits: `work/0695.md`
