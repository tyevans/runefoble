---
id: '0844'
title: One Create Path for Game Sessions
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0065
target_release: 0.9.0
---

# TASK-0844: One Create Path for Game Sessions

## Status
Refined

Source: refactor round 2026-11-18 (user approved).

## Summary
Two routes create a `GameSession` aggregate: `POST /api/v1/sessions/create` (`services/game_session/src/game_session/routers/session.py`) and the campaign session create `POST /api/v1/campaigns/{id}/sessions` (TASK-0706). A session made by the first route is in no campaign session list, so the App Shell never shows it. Keep one create path: the campaign session create.

## Documentation & Architecture Review
- `docs/reference/identifiers-and-uuid-policy.md`, `docs/reference/game-session-child-indexes.md`, `docs/how-to/coordinate-game-session-lobby-and-readiness.md`, `docs/reference/ports-and-endpoints.md`.
- ADR-0011, ADR-0014 (test setup through frontdoors), DoR 9 (no shims).

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)

## Detailed Specification & Implementation Plan
1. Remove `POST /api/v1/sessions/create` from game_session. Move any request field it takes that the campaign create lacks (for example `dm_id`) to the campaign session create only if a product need exists; else drop it.
2. Add one test helper (in `tests/helpers/game_session_setup.py` or `tests/helpers/campaign_setup.py`) that creates a campaign session through the public campaign route and returns its id. Update every test, e2e helper and doc that calls the removed route.
3. Check the gateway, MCP tools, the Watcher and the frontend for callers of the removed route. Update them.

## Frontdoor Test Plan
- `POST /api/v1/sessions/create` answers 404 or 405.
- A session created through the campaign route can be read, joined, started and put in combat (existing tests through the new helper).

## INVEST Criteria Evaluation
Medium (M): one route, many test call sites. Testable through public routes.

## Definition of Done
1. One create path. 2. All tests use the campaign route for setup. 3. Docs updated. 4. `make health-check` passes.
