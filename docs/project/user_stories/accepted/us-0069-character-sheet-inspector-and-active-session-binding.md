---
id: 0069
title: Interactive Character Sheet Inspector and Active Session VTT Binding
status: Accepted
created: 2026-09-27
persona: Marcus (The Voice-First Casual Adventurer) & Sarah (The Absent Player)
feature: FEAT-UI-09
governing_prd: PRD-0006
---

# US-0069 — Interactive Character Sheet Inspector and Active Session VTT Binding

## Governing PRD
- [`PRD-0006: Character Sheet Inventory, Equipment & Condition Aggregation`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)
- [`PRD-0023: Unified Frontend Experience with User Authentication, Campaign Hub, and Session Orchestration`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## User Story

**As a** tabletop player or absent party member,
**I want** to click "Inspect Sheet" on any character in my roster to view and edit their full character sheet (stats, inventory, equipped items, conditions, prepared spells, wardrobe portraits, and AI stand-in guardrails at `#/characters/:characterId`), and when entering a game session, I want the active VTT character card to reflect my selected character rather than a hardcoded dummy,
**So that** my real character stats, inventory, and tactical preferences are active and visible during gameplay.

## Persona Motivations & Permissions
- **Marcus (Player / Casual Adventurer)**: Builds and personalizes characters, equips weapons and armor, inspects spell slots, assigns character to a campaign, and sees his own character's vitals on the tactical board during combat (`owner` of character, `play` permission in campaign).
- **Evelyn (Game Master)**: Inspects party member character sheets, inflicts tactical conditions or absence penalties ("drunk", "curse"), and verifies AC and passive stats (`manage` and `run_session` permission in campaign).
- **Sarah (Absent Player)**: Configures stand-in tactical policies (protect allies, conserve high-level spell slots, avoid melee) and reviews what resources were used while absent (`owner` of character).
- **Nadia (Performer / Thespian)**: Changes character wardrobe variants, inspects condition portraits (bloodied, poisoned), and verifies visual representation (`owner` of character).
- **Alex (Platform Developer)**: Needs standardized REST endpoints for characters with SpiceDB Zanzibar authorization checks (`GET /api/v1/characters`, `POST /api/v1/characters`, `PATCH /api/v1/characters/{id}/campaign`).

## Scenario 1: Player Inspects Full Character Sheet from Roster
```gherkin
Given Marcus is viewing his Character Roster at "#/characters"
When Marcus clicks "Inspect Sheet" on "Valeros of Korvosa"
Then the application navigates to "#/characters/char-valeros"
And mounts the complete "<runefoble-character-sheet>" component
And displays tabs for "Vitals & Stats", "Inventory & Equipment", "Conditions", "Spells", "Wardrobe", and "Stand-In Guardrails"
And Marcus can modify equipped weapons and update guardrail risk thresholds.
```

## Scenario 2: Roster Events Persist via Gateway API
```gherkin
Given Marcus is on "#/characters" and clicks "Create Character"
When Marcus submits the creation wizard with name "Seoni", class "Sorcerer", level 3, max HP 22, AC 12, speed 30
Then a "POST /api/v1/characters" request is sent through the Gateway API
And a new CharacterAggregate is created with full stats, speed, AC, and ability scores
And a SpiceDB relationship tuple "character:char-seoni#owner@user:marcus" is written
And the new character appears in Marcus's roster immediately without page reload.
```

## Scenario 3: Character Assignment and Active VTT Tabletop Sync
```gherkin
Given Marcus has assigned "Valeros" to campaign "Tomb of the Star-Eater"
When Marcus enters the active session at "#/campaigns/4/sessions/session-tomb-14"
Then the active tabletop character card displays "Valeros of Korvosa", "Fighter Lvl 4", AC 18, HP 38/45
And does not display the hardcoded fallback "Kyra the Sun Maiden"
And moving Valeros's token on the board links to his real character ID.
```
