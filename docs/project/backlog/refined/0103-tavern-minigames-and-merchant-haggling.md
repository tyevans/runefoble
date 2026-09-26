---
id: '0103'
title: Interactive Tavern Minigames & Personality-Driven Merchant Haggling
status: Refined
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
governing_prds:
- PRD-0014
governing_stories:
- US-0047
---

# TASK-0103: Interactive Tavern Minigames & Personality-Driven Merchant Haggling

## Status
Refined

## Summary
Implement multiplayer interactive tavern minigames (Liar's Dice, card tournaments, drinking contests with dynamic voice DSP effects) and an NPC merchant haggling system with dynamic temperament states.

## Problem Statement
Settlement visits in virtual tabletop campaigns often degenerate into dry shopping list transactions (PRD-0014, US-0047). Tacticians and social roleplayers like Bram need lively social games to wager gold and dynamic shopkeeper personalities that respond to dialogue, mood, and charisma.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Domain logic in `services/game_session`.
- **ADR-0006: Redis Streams Event Bus**: Event publishing for `MinigameStarted`, `MinigameTurnTaken`, `HagglingNegotiated`.
- **ADR-0011: eventsource-py Core Event Sourcing**: Event-sourced state machines `TavernGameAggregate` and `MerchantAggregate`.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Lit Web Component `<runefoble-tavern-parlor>` in `services/game_session/ui/src/`.

## Product & User Story References
- **Product Requirement**: [`prd-0014-downtime-crafting-and-stronghold-engine.md`](../../product/accepted/prd-0014-downtime-crafting-and-stronghold-engine.md)
- **User Story**: [`us-0047-tavern-minigames-and-merchant-haggling.md`](../../user_stories/accepted/us-0047-tavern-minigames-and-merchant-haggling.md)

## Detailed Specification & Implementation Plan
1. **Tavern Minigame Engine (`services/game_session/src/game_session/minigames.py`)**:
   - Turn-based state machines for Liar's Dice (bluffing, bidding, revealing) and card duels.
   - Drinking contest mechanics applying progressive intoxication status penalties and DSP slurred speech filters (`services/voice_agent`).
2. **Merchant Haggling & Temperament System (`services/game_session/src/game_session/merchants.py`)**:
   - Dynamic merchant mood states (generous, shrewd, hostile, gullible) influencing price curves.
3. **Microfrontend Components & Storybook (`services/game_session/ui/src/`)**:
   - Interactive 3D cup/dice shaker UI in Lit with Bauhaus tokens and Storybook stories.
4. **Frontdoor Blackbox Verification**:
   - Blackbox test suite validating turn state transitions, wagers, and merchant pricing logic.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates independently within `game_session` and leverages `voice_agent` DSP filters asynchronously.
- **Negotiable (N)**: Minigame rules and variation sets.
- **Valuable (V)**: Elevates social roleplay encounters and downtime sessions beyond static sheets.
- **Estimable (E)**: Clearly structured around state machines and event-sourced aggregates.
- **Small (S)**: Modularized under 200 lines per file.
- **Testable (T)**: Fully validated via frontdoor session HTTP routes and published events.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Vendoring**:
   - `<runefoble-tavern-parlor>` built and vendored in `services/game_session/ui/` with `/ui/manifest`.
2. **Strict Line Limit**:
   - All created files strictly under 300 lines in compliance with Hard Invariant 6 (< 500 lines).
3. **Frontdoor Test Verification**:
   - All scenarios verified through public HTTP routes and published CloudEvents (`MinigameStarted`, `MinigameTurnTaken`, `HagglingNegotiated`).
4. **Documentation Integrity**:
   - Diataxis how-to guide authored and documented in `docs/how-to/`.
