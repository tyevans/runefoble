---
id: '0014'
title: Downtime Activities, Alchemical Crafting & Party Stronghold Engine
status: Accepted
created: 2026-09-26
---

# PRD-0014 — Downtime Activities, Alchemical Crafting & Party Stronghold Engine

## Who this is for

Players (like Bram the Tinkerer) and Game Masters (like Evelyn) who desire deep, engaging between-combat interludes, creative item crafting, tavern social games, and persistent base-building.

## What the person cannot do today

- Standard tabletop platforms treat rest periods and non-combat downtime as skipped spreadsheet operations or passive HP recovery.
- Item crafting and potion brewing are reduced to static rulebook lookups with zero experimentation, risk tables, or creative combinations.
- Towns and taverns feel like empty static maps with no interactive wagering minigames, drinking contests, or personality-driven merchant haggling.
- Parties amass gold and raw resources with no tangible outlet to construct, customize, and fortify a persistent campsite, caravan, or stronghold.

## What good looks like

1. **Interactive Campfire & Rest Interludes**:
   - Long and short rests open a dedicated campfire scene with atmospheric lighting, crackling fire audio, and party rest rituals.
   - Collaborative storytelling prompts driven by The Watcher spark in-character banter and character bonding.
2. **Reagent Alchemy & Item Crafting Laboratory**:
   - Drag-and-drop crucible workbench allowing players to mix monster parts, flora, and minerals.
   - Dynamic recipe discovery engine evaluating ingredient affinities, volatile mishap probabilities, and custom potion creation.
3. **Interactive Tavern Minigames & Social Wagering**:
   - Playable Liar's Dice, card games, and arm-wrestling mechanics playable against NPCs or fellow party members.
   - Drinking contests integrating dynamic DSP voice slurring as character intoxication increases.
4. **Personality-Driven Merchant Bartering**:
   - Shopkeepers possess distinct behavioral temperaments (stingy, proud, gullible, eccentric) and mood meters influenced by charisma checks and regional economic events.
5. **Party Stronghold & Campsite Progression**:
   - Upgradable base camp structure (e.g. herbal garden, arcane forge, fortified watchtowers) providing persistent mechanical resting boons to the adventuring party.

## What this does not do

- It does not replace tactical combat or primary campaign questing; it enriches rest cycles and economic gameplay.
- It does not force rigid video game MMO crafting trees; the DM can adjudicate custom reagents and outcomes at any time.

## Checkable Outcomes

1. Alchemical crucible workbench computes recipe outcomes, mishaps, and inventory mutations within 100ms.
2. Tavern minigames (such as Liar's Dice) execute multi-round turns with real-time state synchronization over WebSockets.
3. Merchant negotiation engine dynamically adjusts price offers based on character persuasion rolls and merchant temperaments.
4. Campfire rest boons successfully apply condition and stat modifiers to resting characters upon dawn event trigger.

## Linked User Stories
- [`US-0044: Interactive Campfire Downtime and Alchemical Crafting`](../../user_stories/accepted/us-0044-interactive-campfire-downtime-and-crafting.md)
- [`US-0047: Interactive Tavern Minigames, Gambling and Personality-Driven Merchant Haggling`](../../user_stories/accepted/us-0047-tavern-minigames-and-merchant-haggling.md)

## Implementing Backlog Tasks
- [`TASK-0100: Downtime Activities, Alchemical Crafting & Party Stronghold Engine`](../../backlog/refined/0100-downtime-activities-and-crafting-engine-bc.md)
- [`TASK-0103: Interactive Tavern Minigames & Personality-Driven Merchant Haggling`](../../backlog/proposed/0103-tavern-minigames-and-merchant-haggling.md)
