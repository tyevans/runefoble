---
id: '0044'
title: Interactive Campfire Downtime and Alchemical Crafting
status: Accepted
created: 2026-09-26
persona: Bram (The Tinkerer & Downtime Crafter)
feature: FEAT-DWN-01
governing_prd: PRD-0014
---

# US-0044 — Interactive Campfire Downtime and Alchemical Crafting

## Governing PRD
- [`PRD-0014: Downtime Activities, Alchemical Crafting & Party Stronghold Engine`](../../product/accepted/prd-0014-downtime-crafting-and-stronghold-engine.md)

## User Story

**As a** creative player and artisan during party long rests,  
**I want** an interactive campfire downtime scene where I can experiment with alchemical reagents, forge item infusions, bond with companion pets, and hear collaborative storytelling banter,  
**So that** non-combat rest periods feel like rich, rewarding roleplay interludes rather than skipped bookkeeping.

## Scenario 1: Reagent Experimentation at the Campfire
```gherkin
Given the party initiates a short or long rest
When Bram opens the Campfire Crafting interface and drags "Glowmoss Extract" and "Volcano Ash" into the crucible
Then the alchemical engine calculates reagent compatibility and risk factor
And on success, generates a novel "Radiant Smoke Pellet" with custom tags and mechanics
And updates Bram's inventory and character sheet automatically.
```

## Scenario 2: Party Camp Customization & Rest Boons
```gherkin
Given the party has accumulated resources at their campsite or base
When the party invests in "Reinforced Watchtower" or "Herbal Drying Rack"
Then the camp state aggregate updates with the persistent fortification
And all characters resting in the camp receive a +2 bonus to passive perception or healing surge on their next dawn.
```
