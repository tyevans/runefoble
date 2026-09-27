---
id: 0064
title: Character Roster Management and Campaign Party Assignment
status: Accepted
created: 2026-09-27
persona: Marcus (The Voice-First Casual Adventurer)
feature: FEAT-UI-09
governing_prd: PRD-0023
---

# US-0064 — Character Roster Management and Campaign Party Assignment

## Governing PRD
- [`PRD-0023: Unified Frontend Experience with User Authentication, Campaign Hub, and Session Orchestration`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## User Story

**As a** tabletop player,
**I want** to browse my character roster, build new characters, and assign a specific character to a campaign party,
**So that** my character sheet stats, inventory, conditions, and token representations are automatically synchronized to the campaign and available when joining game sessions.

## Scenario 1: Creating a Character in the Roster
```gherkin
Given Marcus is on the Character Roster view at "#/characters"
When Marcus clicks "Create Character" and completes the wizard with name "Valeros", class "Fighter", level 4, and max HP 45
Then the character aggregate is saved via "POST /api/v1/characters"
And Marcus is assigned the "owner" relation for the character in SpiceDB
And "Valeros" appears as an active card in Marcus's Character Roster.
```

## Scenario 2: Assigning a Character to a Campaign Party
```gherkin
Given Marcus has created "Valeros" and is a member of campaign "Tomb of the Star-Eater"
When Marcus selects "Assign to Campaign" and chooses "Tomb of the Star-Eater"
Then the character is linked to the campaign party
And the character's token and sheet become accessible within the campaign session
And the campaign member view reflects that Marcus is playing "Valeros".
```
