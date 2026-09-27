---
id: '0058'
title: West Marches Shared Persistent World State & Cross-Campaign Trade
status: Accepted
created: 2026-09-26
persona: Rowan (The Chronicler & Worldbuilding Artisan)
feature: FEAT-LRE-04
governing_prd: PRD-0007
---

# US-0058 — West Marches Shared Persistent World State & Cross-Campaign Trade

## Governing PRD
- [`PRD-0007: Campaign Worldbuilding Lore & redstring RAG Engine`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)

## User Story

**As a** campaign coordinator and West Marches guild organizer,  
**I want** multiple distinct adventuring parties to explore and settle the same persistent frontier world, sharing outpost developments, caravan trading networks, and discovery logs,  
**So that** players across different game nights feel part of a grander shared living ecosystem.

## Scenario 1: Cross-Party Discovery Synchronization
```gherkin
Given "Party Blue" discovers the hidden "Sunken Crypt of Arnor" and maps its dungeon entrance
When Party Blue records their expedition milestone in the campaign ledger
Then the discovery is added to the shared regional map index with a "Discovered by Party Blue" timestamp
And when "Party Gold" embarks on an expedition in the same region, their regional atlas displays the entrance pin.
```

## Scenario 2: Caravan Trading and Outpost Resource Ledgers
```gherkin
Given an adventuring party sends an alchemical reagent caravan from Fort Rowan to Highport
When the caravan arrives safely according to the cross-campaign trade scheduler
Then Highport's merchant inventories and crafting workshops unlock rare reagents for any party visiting that settlement.
```
