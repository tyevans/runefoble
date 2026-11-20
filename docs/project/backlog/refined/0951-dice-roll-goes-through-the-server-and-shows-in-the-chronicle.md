---
id: '0951'
title: A Dice Roll Goes Through the Server and Shows in the Chronicle
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds:
- prd-0025-voice-first-release-one
governing_stories:
- us-0006-realtime-spectator-stream-and-chronicle
target_bc: game_session
target_release: 1.0.0
---

# TASK-0951: A Dice Roll Goes Through the Server and Shows in the Chronicle

## Status

Refined. Release One (PRD-0025). Journey step 15 of `.audit/research/r1-core-journeys.md`. The spoken form "roll a d20" is task TASK-0944, not this task.

## Summary

The dice roller computes each roll in the browser. It never calls the owner. Its defaults are a fixed session id, a fixed roller id and the name "Hero". The owner already records a roll at `POST /api/v1/sessions/{id}/roll`, and the gateway already turns the stored `DiceRolled` event into a `dice_rolled` socket frame. But the gateway does not proxy the roll route, so no player roll ever reaches the table. The chronicle also has no live line for a roll.

This task sends every roll to the server, shows the bound character's name, and shows the result in every player's chronicle.

## Problem Statement

Evidence from `.audit/research/r1-core-journeys.md`, section 4, item 6, checked against the code.

- `services/game_session/ui/src/runefoble-dice-roller.ts:19-21`: fixed defaults `sessionId = 'session-1'`, `rollerId = 'player-1'` and `rollerName = 'Hero'`.
- `services/game_session/ui/src/runefoble-dice-roller.ts:123-127`: `roll()` computes the result in the browser with `parseAndRoll`.
- `services/game_session/ui/src/runefoble-dice-roller.ts:132`: the result leaves the element only as a DOM `dice-rolled` event. Nothing in the App Shell listens for it.
- `services/game_session/ui/src/runefoble-dice-roller.ts:90-91`: the window handler reads `detail.result`. The mesh dispatches the raw frame as `detail` (`frontend/src/vtt-mesh-handlers.ts:24` and its dispatch function), so `detail.result` is always undefined. The forced result never applies.
- `services/game_session/src/game_session/routers/session.py:261-262`: the owner route `POST /api/v1/sessions/{session_id}/roll` exists. It takes `RollDiceRequest` (`services/game_session/src/game_session/models/initiative.py:17-20`). Its `roller_name` defaults to `"Player"`, so the client sends the name.
- `services/game_session/src/game_session/aggregate/aggregate.py:63-80`: `record_dice_roll` stores a `DiceRolled` event.
- `gateway/api/src/gateway_api/routers/sessions_proxy.py`: no route proxies `/roll`.
- `gateway/api/src/gateway_api/live_session_frames.py:95`: the gateway builds a `dice_rolled` frame from each `DiceRolled` event. `gateway/api/src/gateway_api/main.py:62` starts the consumer. So the server already sends the frame once a roll is stored.
- `frontend/src/app/session-messages.ts:47-52`: the App Shell appends a line for `chronicle_entry` only. A `dice_rolled` frame adds no chronicle line.
- `frontend/src/services/session-chronicle.ts:23`: the mapper turns a stored `dice_roll` entry into a feed row. So the history view is correct; only the live path is missing.

## Documentation & Architecture Review

- `docs/reference/events-catalog-gameplay.md`: the `DiceRolled` event. Confirm that the frame it produces is listed.
- `docs/reference/ports-and-endpoints.md`: add the gateway roll route.
- `docs/explanation/realtime-voice-and-board-sync.md`: the frame flow for live session events.
- ADR-0015: no substitute name ("Hero") and no substitute session id.
- ADR-0013: the roller is a component of `services/game_session/ui/`. The App Shell mounts it through the plugin slot.

## Product & User Story References

- PRD-0025, "What good looks like", step 5, and Checkable Outcome 1.
- US-0006: the realtime chronicle.

## Detailed Specification & Implementation Plan

1. **Gateway route.** Add `POST /api/v1/sessions/{session_id}/roll` to `gateway/api/src/gateway_api/routers/sessions_proxy.py`. Use the same verified dependency as the other session routes. Forward the body to the owner unchanged. Add the owner route entry to the owner route table that the other session routes use.
2. **Roller element.** In `services/game_session/ui/src/runefoble-dice-roller.ts`, remove the defaults `session-1`, `player-1` and `Hero`. The App Shell passes `sessionId` and the bound character's name. If no character is bound, the roll control is not shown, and the element states that a character must be bound. Do not use a substitute name.
3. **Server result only.** `roll()` posts `{ formula, roller_name, roll_type }` to the gateway route. It shows `total` and `rolls` from the reply. The browser does not compute a roll for a session. `isRolling` ends when the reply arrives or the request fails. A failure shows the server message.
4. **Remove the dead handler.** Remove the `runefoble:dice-rolled` window listener from the roller. The roller shows its own reply. Other players read the roll from the chronicle.
5. **Live chronicle line.** In `frontend/src/app/session-messages.ts`, add a branch for `dice_rolled`. The branch adds a feed row. Its speaker is `rollerName`, its text is `${formula} = ${total}`, and its kind is `dice_roll`. The row uses the same mapping as `frontend/src/services/session-chronicle.ts:23`.
6. **Dice tray.** `services/board_state/ui/src/runefoble-dice-tray-3d.ts` keeps its window listener. It reads the frame fields it already uses.
7. **Storybook.** Update `runefoble-dice-roller` stories for three states: bound, not bound, and failed roll. The stories show zero console errors.
8. **Docs.** Update `docs/reference/ports-and-endpoints.md` and `docs/reference/events-catalog-gameplay.md`.

## Frontdoor Blackbox Test Plan

Playwright BDD scenarios in `e2e/features/session_dice_roll.feature`. Setup uses only the UI: the DM runs the lobby, and the players take their seats in the UI. Each scenario runs in chromium, firefox and webkit.

```gherkin
@US-0006
Feature: Dice rolls reach every player through the server

  Scenario: A roll shows in every player's chronicle with the character name
    Given Evelyn runs the active session "Dice Session" in the UI
    And Valeros and Sarah are seated with their characters in the UI
    When Sarah types "1d20" into the formula field of the dice roller
    And Sarah clicks the roll button
    Then Sarah's chronicle shows a dice entry with the speaker "Sarah of the Mists"
    And Evelyn's chronicle shows the same dice entry within 10 seconds
    And the dice entry shows the formula "1d20" and a total from 1 to 20

  Scenario: A roll survives a page reload
    Given Sarah has rolled "1d20" in the session "Dice Session"
    When Sarah reloads the session view
    Then Sarah's chronicle still shows the dice entry with the speaker "Sarah of the Mists"

  Scenario: A player with no bound character cannot roll
    Given Marcus is signed in with no character bound to the session "Dice Session"
    When Marcus opens the dice roller
    Then no roll button is shown
    And the dice roller says that a character must be bound
```

## Definition of Done

1. `POST /api/v1/sessions/{session_id}/roll` is proxied by the gateway. A test with a live loopback owner upstream checks the forwarded body and the 401 without a token.
2. `git grep -n "Hero\|session-1\|player-1" services/game_session/ui/src/runefoble-dice-roller.ts` returns no match.
3. The roller computes no session roll in the browser. The roll value shown equals the reply `total`.
4. Scenario 1 and scenario 2 pass in chromium, firefox and webkit.
5. A `dice_rolled` frame adds one chronicle row on every open session view.
6. The roller has Storybook stories for its three states. The stories show zero console errors.
7. `docs/reference/ports-and-endpoints.md` and `docs/reference/events-catalog-gameplay.md` match the code.
8. CHANGELOG `[Unreleased]` records the roll route under `Added` and the removed "Hero" default under `Fixed`.
9. No changed source file is over 500 lines.

## Audit Provenance

- Severity: high (the table sees no roll, PRD-0025 step 5)
- Source audits: `.audit/research/r1-core-journeys.md` (section 1, row 15; section 4, item 6)
