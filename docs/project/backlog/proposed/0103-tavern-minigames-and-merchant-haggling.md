---
id: '0103'
title: Interactive Tavern Minigames & Personality-Driven Merchant Haggling
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0010
- TASK-0017
- TASK-0021
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0011
- ADR-0013
target_release: 0.4.0
prd_url: docs/project/product/accepted/prd-0014-downtime-crafting-and-stronghold-engine.md
user_story: US-0047
---

# TASK-0103: Interactive Tavern Minigames & Personality-Driven Merchant Haggling

## Status
Proposed

## Summary
Implement multiplayer interactive tavern minigames (Liar's Dice, card tournaments, drinking contests with dynamic voice DSP effects) and an NPC merchant haggling system with dynamic temperament states.

## Problem Statement
Settlement visits in virtual tabletop campaigns often degenerate into dry shopping list transactions (PRD-0014, US-0047). Tacticians and social roleplayers like Bram need lively social games to wager gold and dynamic shopkeeper personalities that respond to dialogue, mood, and charisma.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace (`services/game_session`).
- **ADR-0006**: Redis Streams Event Bus (`MinigameStarted`, `MinigameTurnTaken`, `HagglingNegotiated`).
- **ADR-0011**: eventsource-py Core Event Sourcing (`TavernGameAggregate`, `MerchantAggregate`).
- **ADR-0013**: Microfrontend Architecture (`<runefoble-tavern-parlor>` component).

## Scope of Work
1. **Tavern Minigame Engine**:
   - Turn-based state machines for Liar's Dice (bluffing, bidding, revealing) and card duels.
   - Drinking contest mechanics applying progressive intoxication status penalties and DSP slurred speech filters (`services/voice_agent`).
2. **Merchant Haggling & Temperament System**:
   - Dynamic merchant mood states (generous, shrewd, hostile, gullible) influencing price curves.
3. **Microfrontend Components & Storybook**:
   - Interactive 3D cup/dice shaker UI in Lit.
4. **Frontdoor Blackbox Verification**:
   - Blackbox test suite validating turn state transitions, wagers, and merchant pricing logic.
