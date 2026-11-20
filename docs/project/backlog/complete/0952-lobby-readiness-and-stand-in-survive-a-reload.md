---
id: '0952'
title: Lobby Readiness and Stand-In Are Kept After a Reload
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds:
- prd-0025-voice-first-release-one
governing_stories:
- us-0065-game-session-lobby-readiness-and-launch
target_bc: game_session
target_release: 1.0.0
---

# TASK-0952: Lobby Readiness and Stand-In Are Kept After a Reload

## Status

Complete

## Summary

The lobby keeps readiness and the stand-in only in the page and in WebSocket frames. The gateway relays those frames and stores nothing. The owner stores readiness, but the gateway does not proxy its route, and the UI never calls it. After a reload every player shows "not ready". The stand-in toggle sends a frame only. It does not call the owner's leave route, so the stand-in is not real. The launch control depends on the DM role only, and no rule uses readiness.

This task stores readiness and the stand-in through owner routes. It also sets the launch rule.

## Problem Statement

Evidence from `.audit/research/r1-core-journeys.md`, section 4, item 5, checked against the code.

- `frontend/src/vtt-mesh-handlers.ts:42-47`: `handleToggleReadiness` changes local state and sends a `player_readiness` frame.
- `frontend/src/vtt-mesh-handlers.ts:50-57`: `handleToggleStandIn` changes local state and sends a `player_stand_in` frame.
- `gateway/api/src/gateway_api/session_frames.py:24-25`: the gateway accepts both frame kinds from clients and relays them.
- `gateway/api/src/gateway_api/session_websocket.py:66-75`: the relay broadcasts the frame and stores nothing.
- `services/game_session/src/game_session/routers/session.py:166-177`: the owner route `POST /api/v1/sessions/{id}/lobby/readiness` stores readiness.
- `services/game_session/src/game_session/models/lobby_transitions.py:15-18`: `with_readiness` writes `lobby_readiness`.
- `gateway/api/src/gateway_api/routers/sessions_proxy.py`: no route proxies `lobby/readiness`, `leave`, or `lobby/character`. The join route is proxied (`:63-73`).
- `services/game_session/src/game_session/routers/session.py:123-148`: the owner route `POST /api/v1/sessions/{id}/leave` records absence and activates the character's AI stand-in (`:144`). The UI never calls it.
- `services/game_session/src/game_session/routers/session.py` (join route): a returning absent player releases the stand-in. This is the return path.
- `frontend/src/services/owner-wire-mappers.ts:82-88`: readiness is read from `lobby_readiness`. Absence is `!player.is_present`. The stand-in toggle never changes `is_present`, so the lobby shows the wrong state after a reload.
- `services/game_session/ui/src/lobby/runefoble-session-lobby.ts:54-56`: `canUserLaunch` returns `isDm` only.
- `frontend/src/app/session-actions.ts:20-33`: `launchSession` calls the start route only.
- `services/game_session/src/game_session/aggregate/session_handlers.py:42-50`: `start()` checks the status only. It does not check readiness.
- `services/game_session/ui/src/lobby/runefoble-session-lobby.ts:317`: the empty state says "Share the session invite link". The lobby has no invite control.

## Documentation & Architecture Review

- `docs/how-to/coordinate-game-session-lobby-and-readiness.md`: describes readiness and absence. Update it with the launch rule and the stand-in routes.
- `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md`: describes the stand-in and the join return path. Keep it consistent with this task.
- `docs/reference/ports-and-endpoints.md`: add the new gateway routes.
- ADR-0015: no hidden default for readiness or absence.
- ADR-0013: the lobby is a component of `services/game_session/ui/`.

## Product & User Story References

- PRD-0025, "What good looks like", step 2, and the principle "A missing player never cancels game night".
- US-0065: pre-game lobby, readiness and launch.

## Detailed Specification & Implementation Plan

1. **Launch rule (decision).** The DM may launch the session at any time from the lobby. Readiness does not block launch. Before launch, the lobby shows the DM a count of seats that are not ready. The owner start route stays as it is.
2. **Gateway routes.** Add gateway proxies for `POST /api/v1/sessions/{id}/lobby/readiness` and `POST /api/v1/sessions/{id}/leave`. The gateway broadcasts `player_readiness` or `player_stand_in` to the session sockets after the owner replies. This follows the start route pattern (`sessions_proxy.py:76-100`).
3. **Remove client frames.** Remove `player_readiness` and `player_stand_in` from `CLIENT_FRAME_PERMISSIONS` (`gateway/api/src/gateway_api/session_frames.py:24-25`). The UI no longer sends these frames. Do not keep a second path.
4. **Stand-in.** Stand-in on calls `POST /leave`. Stand-in off calls `POST /join` with the same character. Both routes are owner routes. The owner route `join` releases the stand-in.
5. **UI calls.** `frontend/src/vtt-mesh-handlers.ts` calls the App Shell data service. The data service calls the gateway routes. The lobby updates from the owner reply and from the broadcast frame.
6. **Reload.** On load, the lobby reads readiness and presence from `GET /api/v1/sessions/{id}`. The mapper already reads them.
7. **Empty state.** Change the text at `runefoble-session-lobby.ts:317` to describe the next step for the DM. It must not refer to a control that the lobby does not have. Use: "No party members have joined yet. Open the campaign to share the invite link."
8. **Storybook.** Update the lobby stories for: not ready, ready, stand-in, and not-ready count before launch. The stories show zero console errors.
9. **Docs.** Update `docs/how-to/coordinate-game-session-lobby-and-readiness.md` with the launch rule.

## Frontdoor Blackbox Test Plan

Playwright BDD scenarios in `e2e/features/session_lobby_state.feature`. Setup uses only the UI. Each scenario runs in chromium, firefox and webkit.

```gherkin
@US-0065
Feature: Lobby readiness and stand-in survive a reload

  Scenario: Ready and stand-in states are kept after a reload
    Given Evelyn runs the lobby "Lobby 16" of the campaign "Reload Campaign" in the UI
    And Valeros and Sarah take their seats in the lobby in the UI
    When Valeros checks "Ready to Play"
    And Sarah checks "Mark Absent (AI Stand-In)"
    And Valeros reloads the lobby page
    Then the "Ready to Play" box of Valeros is checked
    When Evelyn reloads the lobby page
    Then Evelyn's lobby shows Valeros as "Ready"
    And Evelyn's lobby shows the "AI Stand-In" badge on the card of Sarah

  Scenario: The DM can launch while a seat is not ready
    Given Evelyn runs the lobby "Lobby 16" with one seat not ready
    Then Evelyn sees "1 seat not ready" in the lobby
    When Evelyn clicks "Launch Session"
    Then both screens open "#/campaigns/{campaignId}/sessions/{sessionId}"
```

## Definition of Done

1. The gateway proxies the readiness and leave routes. A live loopback owner upstream test checks the forwarded body, the 401 without a token, and the broadcast frame.
2. `git grep -n "player_readiness\|player_stand_in" gateway/api/src/gateway_api/session_frames.py frontend/src` shows no client send path. The only remaining use is the broadcast from the gateway.
3. Scenario 1 and scenario 2 pass in chromium, firefox and webkit.
4. The launch rule is written in `docs/how-to/coordinate-game-session-lobby-and-readiness.md` and in the feature file.
5. The empty-state text at `runefoble-session-lobby.ts:317` no longer refers to a missing control.
6. Lobby Storybook stories show zero console errors.
7. `docs/reference/ports-and-endpoints.md` lists the new routes.
8. CHANGELOG `[Unreleased]` records the routes under `Added` and the reload fix under `Fixed`.
9. No changed source file is over 500 lines.

## Audit Provenance

- Severity: high (readiness and stand-ins are lost on reload, PRD-0025)
- Source audits: `.audit/research/r1-core-journeys.md` (section 1, rows 8 to 10; section 4, item 5)
