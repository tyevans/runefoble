---
id: 0071
title: Campaign Dashboard Creation Idempotency and Lifecycle Management
status: Accepted
created: 2026-09-27
persona: Evelyn (The Overworked Dungeon Master) & Marcus (The Voice-First Casual Adventurer)
feature: FEAT-UI-08
governing_prd: PRD-0023
---

# US-0071 — Campaign Dashboard Creation Idempotency and Lifecycle Management

## Governing PRD
- [`PRD-0023: Unified Frontend Experience with User Authentication, Campaign Hub, and Session Orchestration`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## User Story

**As a** Game Master creating a new campaign realm,
**I want** the campaign creation wizard to submit exactly once and navigate seamlessly to the newly created campaign without creating duplicate entries in my campaign list,
**So that** my campaign dashboard remains organized, predictable, and free of clutter.

## Persona Motivations & Permissions
- **Evelyn (Game Master)**: Creates campaigns for upcoming games. She expects one campaign card to appear per creation action, with immediate navigation to `#campaigns/:id` (`owner` in SpiceDB).
- **Marcus (Player / Party Member)**: Joins or views campaigns without seeing phantom clone campaigns with identical names and descriptions.
- **Alex (Developer / Modder)**: Relies on deterministic REST `POST /api/v1/campaigns` endpoints and decoupled frontend event dispatch where child modal events do not multiply across Shadow DOM boundaries.

## Scenario 1: Exactly-Once Campaign Creation from Modal Wizard
```gherkin
Given Evelyn is on the Campaign Dashboard at "#/campaigns"
When Evelyn opens "+ Create Campaign", enters title "Chronicles of the Astral Sea", and clicks submit
Then the creation form submits exactly once
And the event propagation is stopped within the creator modal
And only one "POST /api/v1/campaigns" request is executed
And the dashboard displays exactly one new campaign card for "Chronicles of the Astral Sea"
And Evelyn is navigated directly to "#/campaigns/camp-..." without seeing duplicate listings.
```

## Scenario 2: Idempotent Client Data Store and De-duplication
```gherkin
Given an unstable network or rapid double-click on the submit button
When multiple create requests are received with identical title and client payload
Then the AppDataService and Gateway API reconcile the requests idempotently
And the campaign list maintains a unique set of campaigns keyed by ID
And returning to "#/campaigns" renders each campaign exactly once.
```
