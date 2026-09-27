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
```gherkin
Given Evelyn has scheduled Session 15 for campaign "Tomb of the Star-Eater"
When Marcus and Sarah join the session lobby at "#/campaigns/4/lobby/15"
Then their presence indicators show "Online"
And Marcus confirms his character "Valeros" and checks "Ready"
And Sarah indicates she will be absent, enabling the AI Stand-In toggle
And the lobby summary updates to show 1 of 2 players ready, 1 absent stand-in.
```

## Scenario 2: DM Launching the Game Session
```gherkin
Given Evelyn sees all active players marked as "Ready" in the lobby
When Evelyn clicks the "Launch Session" button
Then "POST /api/v1/sessions/15/start" is invoked on the backend
And the session state transitions from "lobby" to "active"
And a "SessionStarted" event is published to Redis Streams
And all connected lobby browsers transition automatically to the active VTT board at "#/campaigns/4/sessions/15".
```
