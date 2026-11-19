---
id: 0065
title: Game Session Pre-Game Lobby, Participant Readiness, and Live Launch Orchestration
status: Accepted
created: 2026-09-27
persona: Evelyn (The Overworked Dungeon Master) & Sarah (The Absent Player)
feature: FEAT-UI-10
governing_prd: PRD-0023
---

# US-0065 — Game Session Pre-Game Lobby, Participant Readiness, and Live Launch Orchestration

## Governing PRD
- [`PRD-0023: Unified Frontend Experience with User Authentication, Campaign Hub, and Session Orchestration`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## User Story

**As a** Game Master and participating players,
**I want** a Pre-Game Session Lobby where participants gather before game night, check presence, confirm character selections, toggle readiness, and launch the live game,
**So that** the transition into the tactical VTT occurs smoothly and synchronously for everyone once all players are prepared.

## Scenario 1: Players Gathering and Toggling Readiness

The `{campaignId}` and `{sessionId}` placeholders are the ids from the setup replies (TASK-0652). Names are labels only.
```gherkin
Given Evelyn has created the campaign "Tomb of the Star-Eater" and the session "Session 15" through the gateway
When Marcus and Sarah join the session lobby at "#/campaigns/{campaignId}/lobby/{sessionId}"
Then their presence indicators show "Online"
And Marcus confirms his character "Valeros" and checks "Ready"
And Sarah indicates she will be absent, enabling the AI Stand-In toggle
And the lobby summary updates to show 1 of 2 players ready, 1 absent stand-in.
```

## Scenario 2: DM Launching the Game Session
```gherkin
Given Evelyn sees all active players marked as "Ready" in the lobby
When Evelyn clicks the "Launch Session" button
Then "POST /api/v1/sessions/{sessionId}/start" is invoked on the backend
And the session state transitions from "lobby" to "active"
And a "SessionStarted" event is published to Redis Streams
And all connected lobby browsers transition automatically to the active VTT board at "#/campaigns/{campaignId}/sessions/{sessionId}".
```

## Scenario 3: A Player Who Is Not the DM Does Not See the Launch Control
```gherkin
Given Evelyn runs the campaign "Lantern Vigil" and created the session "Lantern Night"
And Marcus has the "player" role in the campaign
When Marcus opens the lobby of "Lantern Night"
Then the server reports that Marcus cannot run the session
And Marcus does not see the "Launch Session" control
```

## Scenario 4: The Readiness Summary Never Counts the Owner or the DM
```gherkin
Given Evelyn runs the campaign "Lantern Vigil" and created the session "Lantern Night"
When Evelyn opens the lobby of "Lantern Night" and no player has taken a seat
Then the lobby readiness summary reads "No players have joined"
```

## Scenario 5: A Campaign Player Takes a Seat and Becomes Ready
```gherkin
Given Evelyn runs the campaign "Lantern Vigil" and created the session "Lantern Night"
And Mira redeemed Evelyn's player invite to the campaign
And Mira has the character "Mira Thornwake"
When Mira opens the lobby of "Lantern Night" and takes a seat with "Mira Thornwake"
Then "POST /api/v1/sessions/{session_id}/join" is invoked on the gateway
And the lobby readiness summary reads "0 of 1 players ready"
When Mira marks herself ready to play
Then the lobby readiness summary reads "1 of 1 players ready"
```

The Take a Seat control follows the `play` and `run_session` flags of the campaign capabilities reply. The person who runs the session does not see it and does not take a seat (TASK-0889).

## Scenario 6: The DM Sets Up the Battlemap After Launch
```gherkin
Given Evelyn launched "Lobby 15" with Valeros and Sarah seated with campaign characters
When Valeros opens the live session
Then the board area shows "No battlemap yet" with no set-up control
When Evelyn clicks "Set up battlemap" on the empty board
Then "POST /api/v1/boards" is invoked on the gateway
And one token is placed for each seated character through "POST /api/v1/boards/{sessionId}/tokens"
And the tactical board on both screens shows the tokens "Valeros the Bold" and "Sarah of the Mists"
```

A failed board create shows the server message and creates nothing. The executable scenarios are 3 and 4 of `e2e/features/session_lobby_and_vtt.feature` (TASK-0922).
