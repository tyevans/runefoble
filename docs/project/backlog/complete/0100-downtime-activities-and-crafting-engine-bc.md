---
id: '0100'
title: Downtime Activities, Alchemical Crafting & Party Stronghold Engine
status: Complete
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
pr_url: https://github.com/tyevans/runefoble/pull/108
---
# TASK-0100: Downtime Activities, Alchemical Crafting & Party Stronghold Engine

## Status
Refined

## Summary
Implement a downtime activity and crafting engine supporting campfire rest interludes, reagent experimentation with volatile risk tables, and persistent campsite/stronghold base-building.

## Problem Statement
Tabletop downtime is frequently reduced to hand-waved bookkeeping (PRD-0014, US-0044). Players like Bram the Tinkerer need an interactive laboratory to combine monster parts, plants, and minerals into custom concoctions, and a way to invest gold and materials into an evolving party campsite or stronghold that grants resting boons.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Scaffolds domain logic within `services/game_session` and `services/character_sheet`.
- **ADR-0006: Redis Streams Event Bus**: Event publishing for `CraftingAttempted`, `CampfireRestCompleted`, and `StrongholdUpgraded`.
- **ADR-0011: eventsource-py Core Event Sourcing**: Event-sourced aggregates `CraftingAggregate` and `StrongholdAggregate` inheriting from `DeclarativeAggregate`.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Service-vendored Lit component `<runefoble-campfire-crafting>` exposed via `/ui/manifest`.

## Product & User Story References
- **Product Requirement**: [`prd-0014-downtime-crafting-and-stronghold-engine.md`](../../product/accepted/prd-0014-downtime-crafting-and-stronghold-engine.md)
- **User Story**: [`us-0044-interactive-campfire-downtime-and-crafting.md`](../../user_stories/accepted/us-0044-interactive-campfire-downtime-and-crafting.md)

## Detailed Specification & Implementation Plan
1. **Crafting & Alchemical Reagents Aggregate (`CraftingAggregate`)**:
   - Model ingredient affinities, catalysts, and volatile reaction risk matrices in `services/character_sheet/src/character_sheet/crafting.py`.
   - Event-sourced execution of crafting attempts emitting `CraftingSucceeded` or `CraftingMishapOccurred` via `eventsource-py`.
2. **Campfire Rest Interlude & Boons**:
   - Session resting mechanics with collaborative storytelling prompts and resting condition buffs in `services/game_session`.
3. **Party Stronghold & Camp Upgrades (`StrongholdAggregate`)**:
   - Multi-tier camp upgrades (watchtower, forge, herbal rack) stored in domain state with team rest bonuses.
4. **Public REST & WebSocket Endpoints**:
   - `POST /api/v1/crafting/recipes/combine`: Combines reagents and resolves volatile outcome.
   - `POST /api/v1/sessions/{id}/rest/campfire`: Initiates campfire rest sequence.
   - `POST /api/v1/campaigns/{id}/stronghold/upgrade`: Invests gold/materials into campsite facility.
5. **Microfrontend Component**:
   - Lit Web Component `<runefoble-campfire-crafting>` with Storybook stories under `services/game_session/ui/src/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Self-contained bounded context features building upon existing character sheet and game session aggregates.
- **Negotiable (N)**: Specific mishap tables and upgrade tiers can be customized.
- **Valuable (V)**: Provides high-immersion downtime gameplay between tactical dungeon encounters.
- **Estimable (E)**: Follows established `eventsource-py` aggregate and FastAPI router patterns.
- **Small (S)**: Decomposed into focused modules with all files < 250 lines.
- **Testable (T)**: Blackbox frontdoor test suite verifying public HTTP endpoints, event store persistence, and event bus broadcasts.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Domain Events & Aggregates**:
   - Domain events registered with `@register_event` in `libs/runefoble_events`.
   - Aggregates implemented as `DeclarativeAggregate` subclasses with `@handles` methods in accordance with Hard Invariant 2.
2. **Public Frontdoors**:
   - REST endpoints exposed with OpenAPI schemas, verified through Swagger UI aggregator per Hard Invariant 5.
3. **Microfrontend Element**:
   - `<runefoble-campfire-crafting>` rendered with Shadow DOM and Bauhaus design tokens in Storybook.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_campfire_crafting.py` verifying crafting combinations, volatile mishaps, rest boons, and stronghold upgrades via public HTTP routes and Redis Streams event broadcasts.
5. **Quality Gates**:
   - Strictly conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run pytest`, `pnpm run build`, and `make health-check`.
