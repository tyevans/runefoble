---
id: '0073'
title: Customizable Establishments with Assignable NPC Workers and Social Relationship Web
status: Accepted
created: 2026-09-27
persona: Evelyn (The Living World DM)
feature: FEAT-SET-02
governing_prd: PRD-0024
---

# US-0073 — Customizable Establishments with Assignable NPC Workers and Social Relationship Web

## Governing PRD
- [`PRD-0024: Settlement Haven Builder, Living Urban Ecosystem & Mobile Web Minigames`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)

## User Story

**As a** Game Master and worldbuilder,  
**I want** to place and customize establishments (such as bakeries, weapon shops, taverns, and casinos) within settlements and assign NPC workers equipped with dynamic inventories, personality temperaments, secret knowledge, and interconnected social relationships,  
**So that** shop visits and downtime interludes are fueled by emergent interpersonal drama, living mercantile operations, and organic narrative quest hooks.

## Scenario 1: Constructing a Weapon Shop and Assigning an Armorer
```gherkin
Given a market town with an available commercial plot in the Artisan Quarter
When Evelyn adds an establishment of type "Weapon Smithy" named "The Ember Anvil"
And assigns an NPC blacksmith "Torvin Ironbreaker" with a "Gruff but Honorable" temperament
Then the establishment generates operational stats, inventory shelves, and backroom forge facilities
And Torvin's personal profile links his apprentices, supplier debts to the mining syndicate, and weapon blueprints.
```

## Scenario 2: Dynamic NPC Interpersonal Drama and Supply Disruption
```gherkin
Given the town's Warm Hearth Bakery relies on flour delivered by the local riverside mill
When the miller is waylaid by river bandits and shipments fail to arrive
Then the baker's mood temperament shifts toward "Anxious and Desperate"
And the baker's inventory reflects a bread shortage with elevated prices
And the baker logs a distress proclamation onto the town bulletin board seeking adventurer assistance.
```
