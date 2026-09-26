---
id: '0100'
title: Downtime Activities, Alchemical Crafting & Party Stronghold Engine
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0009
- TASK-0018
- TASK-0048
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0011
- ADR-0013
target_release: 0.4.0
prd_url: docs/project/product/accepted/prd-0014-downtime-crafting-and-stronghold-engine.md
user_story: US-0044
---

# TASK-0100: Downtime Activities, Alchemical Crafting & Party Stronghold Engine

## Status
Proposed

## Summary
Implement a downtime activity and crafting engine supporting campfire rest interludes, reagent experimentation with volatile risk tables, and persistent campsite/stronghold base-building.

## Problem Statement
Tabletop downtime is frequently reduced to hand-waved bookkeeping (PRD-0014, US-0044). Players like Bram the Tinkerer need an interactive laboratory to combine monster parts, plants, and minerals into custom concoctions, and a way to invest gold and materials into an evolving party campsite or stronghold that grants resting boons.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace (`services/game_session` and `services/character_sheet`).
- **ADR-0006**: Redis Streams Event Bus (`CraftingAttempted`, `CampfireRestCompleted`, `StrongholdUpgraded`).
- **ADR-0011**: eventsource-py Core Event Sourcing (`CraftingAggregate`, `StrongholdAggregate`).
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring (`<runefoble-campfire-crafting>` custom element).

## Scope of Work
1. **Crafting & Alchemical Reagents Aggregate**:
   - Model ingredient affinities, catalysts, and volatile reaction risk matrices.
   - Event-sourced execution of crafting attempts emitting `CraftingSucceeded` or `CraftingMishapOccurred`.
2. **Campfire Rest Interlude & Boons**:
   - Session resting mechanics with collaborative storytelling prompts and resting condition buffs.
3. **Party Stronghold & Camp Upgrades**:
   - Multi-tier camp upgrades (watchtower, forge, herbal rack) stored in domain state with team rest bonuses.
4. **Microfrontend Component**:
   - Lit Web Component `<runefoble-campfire-crafting>` with Storybook stories.
5. **Frontdoor Blackbox Verification**:
   - Blackbox test suite covering public HTTP endpoints and event emissions.
