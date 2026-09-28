---
id: 0067
title: Campaign Detail View, Setting Management, and Session Scheduling
status: Accepted
created: 2026-09-27
persona: Evelyn (The Overworked Dungeon Master) & Marcus (The Voice-First Casual Adventurer)
feature: FEAT-UI-12
governing_prd: PRD-0023
---

# US-0067 — Campaign Detail View, Setting Management, and Session Scheduling

## Governing PRD
- [`PRD-0023: Unified Frontend Experience with User Authentication, Campaign Hub, and Session Orchestration`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## User Story

**As a** Game Master preparing game night or a Player coordinating with my party,
**I want** a dedicated Campaign Command Center at `#/campaigns/:id` that renders a rich campaign hero header (title, setting, system ruleset, status, cover art, and DM profile), an "Edit Campaign" dialog for managers, a structured session scheduler, and deep links into party characters and campaign lore,
**So that** I have a single, cohesive interface to manage our ongoing world and schedule sessions rather than relying on an empty, disconnected stub page with static fallbacks.

## Persona Motivations & Permissions
- **Evelyn (Game Master / Owner)**: Needs to update campaign settings (system edition, description, setting lore), schedule future game sessions with titles and target times, immediately create pre-game lobbies, and administer Zanzibar member roles (`manage` and `run_session` permissions).
- **Marcus (Player)**: Views the campaign premise and assigned party members, checks upcoming session times, and clicks one button to enter the active pre-game lobby (`view` permission).
- **Sarah (Absent Player)**: Visits the campaign page to review session history and ensure her character's AI stand-in policy is configured for the next gathering.
- **Devon (Spectator)**: Inspects public campaign details, party composition, and clicks to watch the live session overlay.

## Scenario 1: Game Master Views and Edits Campaign Details
```gherkin
Given Evelyn is an authenticated user with "owner" relation on campaign "camp-1790564858218"
When Evelyn navigates to "#/campaigns/camp-1790564858218"
Then the application fetches campaign metadata from "GET /api/v1/campaigns/camp-1790564858218"
And renders a Bauhaus hero header with title "Tomb of the Star-Eater", setting badge "Spelljammer Astral Void", and system pill "5e"
And displays an "Edit Campaign" button visible only to users with "manage" permission
When Evelyn clicks "Edit Campaign" and updates the description to "An epic journey through astral horrors."
Then a "PATCH /api/v1/campaigns/camp-1790564858218" request is dispatched
And the campaign header reflects the updated description immediately.
```

## Scenario 2: Game Master Schedules a Session or Creates Staging Lobby
```gherkin
Given Evelyn is viewing her campaign page at "#/campaigns/camp-1790564858218"
When Evelyn clicks "+ New Session" in the session list
Then a session creation modal opens prompting for session title, scheduled date/time, and initial status ("lobby" vs "upcoming")
When Evelyn enters title "Session 16: The Astral Spire" and clicks "Create Session"
Then a "POST /api/v1/campaigns/camp-1790564858218/sessions" request is sent to the Gateway API
And the new session record is created in the backend store
And the session appears in the session list with an "Enter Lobby" button
And navigating to the lobby connects players to the new session ID.
```

## Scenario 3: Player Navigates Campaign Tabs and Joins Session
```gherkin
Given Marcus is a party member with "player" role in campaign "camp-1790564858218"
When Marcus navigates to "#/campaigns/camp-1790564858218"
Then Marcus sees the campaign hero header without the "Edit Campaign" button
And Marcus can switch between "Overview & Sessions", "Party Roster", and "Campaign Codex" tabs
When Marcus clicks "Party Roster"
Then the view mounts the campaign party character assignment view at "#/campaigns/camp-1790564858218/characters"
And when an active session exists, Marcus clicks "Join Tabletop" to transition directly into the live VTT.
```
