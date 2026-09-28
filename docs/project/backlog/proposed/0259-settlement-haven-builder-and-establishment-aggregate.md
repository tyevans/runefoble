---
id: '0259'
title: Settlement Haven Builder and Establishment Aggregate Domain Model
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0164
- TASK-0208
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0024
governing_stories:
- US-0072
- US-0073
target_release: 0.8.0
---

# TASK-0259: Settlement Haven Builder and Establishment Aggregate Domain Model

## Status
Proposed

## Summary
Implement the core event-sourced `SettlementAggregate` and `EstablishmentAggregate` within `services/game_session/` (or dedicated bounded context), providing domain events, commands, and read projections for managing settlement scales (hamlet, village, market town, city, metropolis), district zoning, and establishment lifecycle.

## Problem Statement
While Runefoble supports persistent havens in West Marches campaigns, there is no domain model for granular settlement layouts, geographic placement logic, district zoning, or establishment management. Towns cannot record constructed bakeries, taverns, casinos, or weapon shops with operational statuses and civic attributes.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/charter-frontier-settlements-and-havens.md`: Settlement haven charters and rest boons.
  - `docs/how-to/define-event-sourced-aggregates.md`: `eventsource-py` declarative aggregate conventions.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Enforcing campaign member write permissions for civic construction.
  - **ADR-0007: Domain-Driven Design Architecture**: Aggregate boundaries separating settlements from establishments.
  - **ADR-0011: eventsource-py Core Event Sourcing**: Immutable domain event streams.

## Product & User Story References
- **Product Requirement**: [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- **User Story**: [`us-0072-mobile-responsive-settlement-browser-and-town-builder.md`](../../user_stories/accepted/us-0072-mobile-responsive-settlement-browser-and-town-builder.md)
- **User Story**: [`us-0073-customizable-establishments-and-assignable-npc-workers.md`](../../user_stories/accepted/us-0073-customizable-establishments-and-assignable-npc-workers.md)

## Detailed Specification & Implementation Plan
1. **Domain Events (`libs/runefoble_events/settlements.py`)**:
   - `SettlementFounded`: `settlement_id`, `campaign_id`, `name`, `scale`, `biome`, `coordinates`.
   - `SettlementTierUpgraded`: `settlement_id`, `old_tier`, `new_tier`, `unlocked_districts`.
   - `EstablishmentConstructed`: `establishment_id`, `settlement_id`, `district_id`, `category`, `name`.
   - `EstablishmentUpgraded`: `establishment_id`, `tier`, `added_amenities`.
2. **Aggregates & Handlers**:
   - `SettlementAggregate`: Validates tier prerequisites, maximum district slots per scale, and civic prosperity metrics.
   - `EstablishmentAggregate`: Manages establishment state, capacity, operating costs, and amenities.
3. **HTTP API Routes**:
   - `POST /api/v1/campaigns/{campaign_id}/settlements`: Found settlement.
   - `GET /api/v1/campaigns/{campaign_id}/settlements/{settlement_id}`: Query settlement projection.
   - `POST /api/v1/settlements/{settlement_id}/establishments`: Construct establishment.

## Definition of Done
- Domain events registered with `@register_event` and serializable as CloudEvents.
- Aggregates strictly enforce invariants without reaching into raw database tables.
- All files remain under 400 lines per `AGENTS.md` Rule 6.
