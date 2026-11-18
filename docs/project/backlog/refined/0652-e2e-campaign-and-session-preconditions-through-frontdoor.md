---
id: '0652'
title: E2E Scenarios Create Their Campaign and Session Through Public Frontdoors
status: Refined
created: 2026-11-17
dependencies:
- TASK-0650
governing_adrs:
- ADR-0014
- ADR-0007
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0065
target_release: 0.9.0
---

# TASK-0652: E2E Scenarios Create Their Campaign and Session Through Public Frontdoors

## Status
Refined

## Summary
The lobby and VTT feature depends on a seeded campaign "4" and session "15" that nothing creates. The expected URL `#/campaigns/4/sessions/15` is hard-coded. The smoke scenario that "prepares a campaign" never uses the campaign it creates. Each scenario must create its own campaign and session through public routes in its Background, use the returned ids, and never hard-code an id.

## Problem Statement
- `e2e/features/session_lobby_and_vtt.feature:8` says "hosting session 'Lobby 15' for campaign '4'". `vtt_steps.ts:13-21` and `:33-34` take the campaign id from that text.
- Nothing creates campaign 4 or session 15 through `POST /api/v1/campaigns` or a session route before the steps run.
- `session_lobby_and_vtt.feature:21` hard-codes `#/campaigns/4/sessions/15`.
- `e2e/features/smoke.feature:17-25` ("Dungeon Master prepares campaign through public frontdoor") creates a campaign with `campaign "..." exists`, then asserts only the heading and hash. It never uses the campaign.

## Documentation & Architecture Review
- `e2e/support/frontdoor_api.ts` already calls public routes (`/api/v1/campaigns`, `/characters`, `/roles`, `/invites`, `/members`). Extend it with a session helper. Do not add database access.
- ADR-0014: test setup goes through the frontdoor. ADR-0007: the session belongs to the game session bounded context, so setup calls its public route through the gateway.
- `docs/how-to/test-user-flows-with-playwright-bdd.md` describes Background setup. Update it with the pattern.

## Product & User Story References
- [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
- [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)

## Detailed Specification & Implementation Plan
1. Add `createSession(campaignId, title)` to `e2e/support/frontdoor_api.ts`. It calls the public session creation route and returns the id. It throws on a non-2xx response.
2. Rewrite the Background of `session_lobby_and_vtt.feature` as: a DM and players exist; the DM creates campaign "Lobby Campaign" and session "Lobby 15" through the public routes; the scenario stores both ids in the world object.
3. Replace the literal URL assertion with a pattern built from the stored ids, for example `#/campaigns/{campaignId}/sessions/{sessionId}`.
4. Remove the `'4'` and `'15'` literals from step definitions. Campaign and session names in feature text are labels only.
5. Rewrite the smoke scenario so that its campaign is used: the DM opens the campaign it created and sees its title in the header.
6. Each feature file keeps its own Background. No scenario depends on another scenario's data.

## Frontdoor Blackbox Test Plan
- `session_lobby_and_vtt.feature` passes with campaign and session created in the Background. Before the change the scenario FAILS when the seeded campaign is absent (run against an empty database in a local run).
- `smoke.feature` "Dungeon Master prepares campaign through public frontdoor" asserts the created campaign title in the header.
- Negative check: if `POST /api/v1/campaigns` returns 422 in setup, the scenario fails at the Background step with the response body in the message.

## Definition of Done
1. `grep -rn "campaign '4'\|sessions/15\|campaignId = '4'" e2e/features e2e/steps` returns no match.
2. Each scenario's Background creates its own data through public routes.
3. The lobby, VTT, and smoke scenarios pass in all three browsers.
4. `frontdoor_api.ts` has no direct database or private-state access (verified by review).
5. Each file is under 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w2-e2e-bdd.md`
