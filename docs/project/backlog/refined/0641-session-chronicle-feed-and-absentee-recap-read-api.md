---
id: '0641'
title: Session Chronicle Feed and Absentee Recap Read API Replace Canned App Shell Data
status: Refined
created: 2026-11-17
dependencies:
- TASK-0640
governing_adrs:
- ADR-0006
- ADR-0007
- ADR-0011
- ADR-0013
governing_prds:
- PRD-0002
- PRD-0012
- PRD-0023
governing_stories:
- US-0005
- US-0027
- US-0040
target_release: 0.9.0
severity: high
source_audits:
- w2-app-shell.md
---

# TASK-0641: Session Chronicle Feed and Absentee Recap Read API Replace Canned App Shell Data

## Status
Refined

## Summary
The session chronicle feed and the absentee recap are hard-coded. `fetchSessionEvents()` returns `FALLBACK_SESSION_EVENTS`, and `triggerAbsenteeRecap()` writes the story of "Valeros of Korvosa". No gateway route exists for either. Add two public read routes that the `game_session` service backs with its own event data. The App Shell calls them and shows an empty state when no data exists.

## Problem Statement
- `frontend/src/services/app-data-service.ts:170` `fetchSessionEvents()` ignores its argument and returns `FALLBACK_SESSION_EVENTS`. The gateway route inventory has no `/api/v1/sessions/{id}/events`.
- `frontend/src/runefoble-app.ts:207-210` `triggerAbsenteeRecap()` writes fixed content: persona "The Cautious Defender", penalties `drunk` and `foolishness`, highlight "Parried a critical strike", and `hpDelta -4`. It runs whenever a stand-in is deactivated, with no backend call.
- The tutorial `docs/tutorials/02-running-your-first-session.md` (step 2) shows the fixture feed as live output. TASK-0658 corrects it after this task.

## Documentation & Architecture Review
- `docs/reference/events-schema.md` and `docs/reference/ports-and-endpoints.md` must list the two new routes (DoD 4 of `backlog/README.md`).
- ADR-0011: the chronicle is a read projection over the session event stream. It is not a new store. Any write path goes through an aggregate.
- ADR-0013: the component that renders the chronicle belongs to `services/game_session/ui` or `services/campaign_analytics/ui`. Decide at refinement; the App Shell must not own the rendering logic.
- Overlaps proposed TASK-0461 (absentee telemetry and audio recap companion API) and TASK-0459 (chronicle projection). This task covers only the two public reads that the App Shell needs. TASK-0461 keeps the companion and audio API.

## Product & User Story References
- [`prd-0002-missing-player-ai-stand-in-with-penalties.md`](../../product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md)
- [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- [`us-0005-absentee-session-chronicle-recap.md`](../../user_stories/accepted/us-0005-absentee-session-chronicle-recap.md)
- [`us-0027-absentee-character-resource-ledger-and-recap-reel.md`](../../user_stories/accepted/us-0027-absentee-character-resource-ledger-and-recap-reel.md)

## Detailed Specification & Implementation Plan
1. Gateway (thin, auth and routing only): add `GET /api/v1/sessions/{session_id}/events` and `GET /api/v1/sessions/{session_id}/absentee-recap` in a new router file under `gateway/api/src/gateway_api/routers/`. Check `view` on the session through SpiceDB (ADR-0001). Proxy to `game_session`.
2. `game_session` (owning bounded context): add a read endpoint for session events, backed by the event store that the service is configured to use. Add an absentee-recap query that derives its content from stand-in and penalty events. It must not contain fixed names, penalties, or amounts.
3. When the session has no events, both endpoints return an empty list or an empty recap, not an error.
4. App Shell: `fetchSessionEvents()` calls the new route. `triggerAbsenteeRecap()` is replaced by a call to the recap route, and the recap view shows an empty state when there is nothing to show.
5. Delete `FALLBACK_SESSION_EVENTS` from production code (TASK-0640 moves fixtures to tests and stories).
6. Each new route appears in its service `/openapi.json` and in the Swagger aggregator list (Hard Invariant 5).
7. Every changed Python file stays under 500 lines. Split the recap query into its own module if needed.

## Frontdoor Blackbox Test Plan
Pytest through public HTTP (`tests/test_blackbox_session_chronicle.py`):
- Given a session with a player who was replaced by a stand-in and a penalty event, when a member calls `GET /api/v1/sessions/{id}/events`, then the response contains the `SessionPenaltyApplied` event with the penalty name.
- Given the same session, when a member calls `GET /api/v1/sessions/{id}/absentee-recap`, then the response's penalties equal the events, not the fixed sample values.
- Given a session with no events, both routes return 200 with empty collections.
- A non-member gets 403 from the gateway.
- Before the fix the routes return 404 and the App Shell shows fixture rows. After the fix the tests PASS.

Playwright BDD (`e2e/features/absentee_recap.feature`): setup uses only public routes (session creation, stand-in activation through the lobby UI). The scenario asserts the recap text shown in the App Shell matches the penalty the API reports.

## Definition of Done
1. Both routes exist in the gateway and in `game_session`, with `/openapi.json` coverage.
2. The App Shell no longer contains "Valeros of Korvosa", "Cautious Defender", or `FALLBACK_SESSION_EVENTS`. Verified by a test that greps `frontend/src`.
3. Pytest blackbox suite and Playwright BDD scenario pass.
4. `docs/reference/ports-and-endpoints.md` and `docs/reference/events-schema.md` list the routes.
5. Changelog entry under `[Unreleased]`.
6. Files changed stay under 500 lines each.
