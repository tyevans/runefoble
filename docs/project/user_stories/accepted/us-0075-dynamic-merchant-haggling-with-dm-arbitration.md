---
id: '0075'
title: Dynamic Merchant Haggling Engine with Temperament State and DM Controls
status: Accepted
created: 2026-09-27
persona: Lady Nicole (The Merchant-Tycoon & Supply-Chain Opportunist)
feature: FEAT-SET-04
governing_prd: PRD-0024
---

# US-0075 — Dynamic Merchant Haggling Engine with Temperament State and DM Controls

## Governing PRD
- [`PRD-0024: Settlement Haven Builder, Living Urban Ecosystem & Mobile Web Minigames`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)

## User Story

**As a** mercantile player negotiating for weapons, potions, or rare goods,  
**I want** an interactive bartering interface that evaluates dialogue tactics against the merchant's personality temperament, patience, and regional market margins, while providing the DM with real-time override controls,  
**So that** shopping encounters are strategic, suspenseful social minigames where clever bargaining and roleplay yield meaningful economic rewards without subverting the DM's narrative intent.

## Scenario 1: Haggling with an Armorer over a Masterwork Blade
```gherkin
Given Lady Nicole browses the weapon inventory at "The Ember Anvil"
When Nicole offers 70 gold for a longsword listed at 100 gold and selects the "Bulk Order Promise" gambit
Then the system rolls Nicole's Persuasion check against the blacksmith's "Greedy but Skeptical" temperament
And the blacksmith's patience meter decreases while proposing a counter-offer of 85 gold
And an in-character merchant dialogue bark is rendered to the shop interface.
```

## Scenario 2: DM Real-Time Negotiation Override and Narrative Intervention
```gherkin
Given an ongoing heated bartering exchange between Nicole and an alchemist
When the Game Master observes the player's exceptional in-person verbal roleplay at the table
Then the DM adjusts the merchant's mood slider from "Impatient" to "Charmed" using DM controls
And accepts the discounted trade immediately with a custom DM-authored voice narration bark
Updating the character's inventory and party ledger without disrupting the game flow.
```
