---
id: 0063
title: Campaign Creation, Dashboard Hub, and SpiceDB Zanzibar Member Access Control
status: Accepted
created: 2026-09-27
persona: Evelyn (The Overworked Dungeon Master)
feature: FEAT-UI-08
governing_prd: PRD-0023
---

# US-0063 — Campaign Creation, Dashboard Hub, and SpiceDB Zanzibar Member Access Control

## Governing PRD
- [`PRD-0023: Unified Frontend Experience with User Authentication, Campaign Hub, and Session Orchestration`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## User Story

**As a** Game Master running multiple tabletop campaigns,
**I want** a dedicated Campaign Dashboard where I can create new campaigns, view all campaigns I own or play in, generate invite links, and manage member roles (DM, Player, Spectator),
**So that** I can organize my groups and enforce strict SpiceDB Zanzibar authorization boundaries directly from the browser UI without manual database interventions.

## Scenario 1: Creating a Campaign from the Dashboard
```gherkin
Given Evelyn is logged in and viewing the Campaign Dashboard at "#/campaigns"
When Evelyn clicks "Create Campaign" and enters title "Shadows of Drakkenheim" and setting "Gothic Fantasy"
Then a POST request is sent to "/api/v1/campaigns"
And a new campaign is created in the backend
And Evelyn is granted the "owner" relation in SpiceDB Zanzibar schema
And the new campaign appears immediately on her Campaign Dashboard with an "Owner" badge.
```

## Scenario 2: Inviting a Player and Assigning Zanzibar Roles
```gherkin
Given Evelyn is managing the campaign "Shadows of Drakkenheim" at "#/campaigns/4"
When Evelyn generates an invite link and sends it to Marcus
And Marcus accepts the invite code
Then Marcus is added to the campaign membership list
And Evelyn assigns Marcus the "player" role
And a SpiceDB relationship tuple "campaign:4#player@user:marcus" is written
And Marcus's dashboard reflects player access to campaign assets.
```
