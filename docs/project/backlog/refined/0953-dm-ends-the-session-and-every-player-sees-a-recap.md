---
id: '0953'
title: The DM Ends the Session and Every Player Sees a Recap
status: Refined
created: 2026-11-19
dependencies:
- '0951'
governing_adrs:
- ADR-0011
- ADR-0013
- ADR-0014
governing_prds:
- prd-0025-voice-first-release-one
governing_stories:
- us-0005-absentee-session-chronicle-recap
- us-0006-realtime-spectator-stream-and-chronicle
target_bc: game_session
target_release: 1.0.0
---

# TASK-0953: The DM Ends the Session and Every Player Sees a Recap

## Status

Refined. Release One (PRD-0025). Journey step 19 of `.audit/research/r1-core-journeys.md`.

## Summary

No control in the App Shell ends a session. The owner has a route, `POST /api/v1/sessions/{id}/end`. The gateway does not proxy it, and the UI never calls it. The chronicle maps a `SessionEnded` event to a feed row, but no player receives the end. The recap components exist but are not mounted.

This task adds a DM-only end control, the gateway route, a `session_ended` socket frame, and a recap view built from the session chronicle.

## Problem Statement

Evidence from `.audit/research/r1-core-journeys.md`, section 2, checked against the code.

- `services/game_session/src/game_session/routers/session.py:81-92`: the owner route `POST /api/v1/sessions/{session_id}/end` calls `session.end()`. It requires `session.control` (`SessionController`).
- `services/game_session/src/game_session/aggregate/aggregate.py:104-112`: `end()` records `SessionEnded` unless the status is already `ended`. A lobby session can end too. The release rule (end from `active` only) is set by this task.
- `gateway/api/src/gateway_api/routers/sessions_proxy.py`: no route proxies `/end`.
- `gateway/api/src/gateway_api/campaign_actions.py:92-93` and `:113`: a WebSocket action `end_session` exists on the campaign socket. No UI sends it.
- `frontend/src/views/session-view.ts:31-62`: the session view has no end control.
- `frontend/src/services/app-data-service.ts:179`: `startSession` is the only session state change. No end method exists.
- `frontend/src/app/session-socket.ts:110`: the socket handles `session_started` only.
- `frontend/src/services/session-chronicle.ts:11` and `:23`: `session_ended` is a feed kind, and the mapper turns it into a generic system row.
- `services/game_session/src/game_session/chronicle.py:106-112`: `SessionEnded` maps to a `session_ended` chronicle entry.
- `gateway/api/src/gateway_api/routers/sessions_proxy.py:155-163`: the gateway proxies `GET /api/v1/sessions/{id}/events`. The UI reads it through `frontend/src/services/app-data-service.ts:203`.
- `services/character_sheet/ui/src/runefoble-absentee-recap.ts:5`: the recap element is defined and exported. No App Shell file mounts it, and it shows the stand-in recap, not the session recap.

## Documentation & Architecture Review

- `docs/reference/speculative-feature-inventory.md:46` lists `FEAT-WAT-05`, the chronicler recap, as planned. Update the row when this task lands.
- `docs/reference/microfrontend-architecture.md:102` lists `<runefoble-absentee-recap>` as an in-use element. It is not mounted in the App Shell. Correct the catalog text.
- `docs/how-to/project-campaign-analytics-and-chronicle-timeline.md`: the chronicle timeline. Keep its terms.
- `docs/reference/ports-and-endpoints.md`: add the gateway end route.
- ADR-0011: the end is an aggregate event. The recap reads the event stream, not a second store.
- ADR-0013: the recap is a component of `services/game_session/ui/`. The App Shell mounts it.

## Product & User Story References

- PRD-0025, "What good looks like", step 7, and Checkable Outcome 1.
- US-0005: the absentee chronicle recap. This task builds the session recap that US-0005 needs at table level.
- US-0006: the realtime chronicle.

## Detailed Specification & Implementation Plan

1. **Owner rule.** In `aggregate.py`, `end()` accepts only `active` status. A lobby session returns 400. Add a test in the game_session route tests.
2. **Gateway route.** Add `POST /api/v1/sessions/{session_id}/end` to `sessions_proxy.py` with the verified dependency. After the owner replies with an `ended` status, the gateway broadcasts `{ "type": "session_ended", "sessionId": ..., "status": "ended" }`. Validate the owner reply with a model, as the start route does (`sessions_proxy.py:76-100`). A reply without a status returns 502.
3. **DM control.** Add an "End Session" button to `frontend/src/views/session-view.ts`. It shows only when `campaignCapabilities.run_session` is true and the session status is `active`. A confirm step follows the click. The App Shell data service gets `endSession(sessionId)`.
4. **Socket.** In `frontend/src/app/session-socket.ts`, handle `session_ended`. Set the view state to `ended`. The App Shell then shows the recap.
5. **Recap element.** Add `<runefoble-session-recap>` in `services/game_session/ui/src/recap/runefoble-session-recap.ts`. It takes the feed entries from `fetchSessionEvents`. It lists the lines in commit order, with the summary text. It shows counts for dice rolls, token moves and stand-in actions. It has no fallback text for a missing summary.
6. **Reload.** When `GET /api/v1/sessions/{id}` reports `ended`, the App Shell shows the recap on load.
7. **Storybook.** Add `runefoble-session-recap.stories.ts` with an empty recap, a recap with dice and move lines, and a recap with a stand-in action. The stories show zero console errors.
8. **Docs.** Update the speculative inventory row, the microfrontend catalog text, and the ports table.

## Frontdoor Blackbox Test Plan

Playwright BDD scenarios in `e2e/features/session_end_and_recap.feature`. Setup uses only the UI. Each scenario runs in chromium, firefox and webkit.

```gherkin
@US-0005 @US-0006
Feature: The DM ends the session and every player sees a recap

  Scenario: The DM ends an active session and each player sees the recap
    Given Evelyn runs the active session "End Session Run" in the UI
    And Valeros rolls "1d20" in the dice roller in the UI
    When Evelyn clicks "End Session" and confirms
    Then Evelyn's view shows the recap with "Session started." and "Session ended."
    And Valeros's view shows the recap within 10 seconds
    And the recap of Valeros lists the dice entry "1d20"
    And Valeros has no "End Session" control

  Scenario: The recap stays after a reload
    Given the session "End Session Run" has ended in the UI
    When Valeros reloads the session view
    Then Valeros sees the recap with "Session ended."

  Scenario: A player cannot end the session
    Given Valeros is on the active session "End Session Run" in the UI
    Then no "End Session" control is shown to Valeros
```

## Definition of Done

1. `POST /api/v1/sessions/{id}/end` is proxied by the gateway. A live loopback owner upstream test checks the 401 without a token, the forwarded call, and the `session_ended` broadcast.
2. The owner returns 400 for an end from `lobby`. A route test covers it.
3. `session_ended` is handled in `frontend/src/app/session-socket.ts`. `git grep -n session_ended frontend/src/app` shows the handler.
4. The three scenarios pass in chromium, firefox and webkit.
5. `<runefoble-session-recap>` has Storybook stories. The stories show zero console errors.
6. `docs/reference/speculative-feature-inventory.md`, `docs/reference/microfrontend-architecture.md` and `docs/reference/ports-and-endpoints.md` match the code.
7. CHANGELOG `[Unreleased]` records the end route and the recap under `Added`.
8. No changed source file is over 500 lines.

## Audit Provenance

- Severity: high (a session never ends, PRD-0025)
- Source audits: `.audit/research/r1-core-journeys.md` (section 2; section 4, item 7)
