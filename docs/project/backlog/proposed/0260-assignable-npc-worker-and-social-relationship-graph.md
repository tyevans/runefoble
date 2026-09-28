---
id: '0260'
title: Assignable NPC Worker Engine and Social Relationship Graph
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0259
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0024
governing_stories:
- US-0073
target_release: 0.8.0
---

# TASK-0260: Assignable NPC Worker Engine and Social Relationship Graph

## Status
Proposed

## Summary
Build the worker management and social relationship graph subsystem for establishments, enabling NPCs to be assigned to roles (head baker, armorer, croupier, bouncer, apprentice) with distinct personality traits, dynamic inventories, memory of town events, and interconnected interpersonal ties.

## Problem Statement
Town establishments currently lack living staff. Merchants are stateless entities with static compendium price lists rather than dynamic NPCs with wages, morale, vendor margins, personal loyalties, or interpersonal rivalries that react to player deeds and regional events.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/simulate-npc-faction-agendas-and-world-ticks.md`: NPC faction agendas and simulation ticks.
  - `docs/how-to/index-campaign-lore-with-redstring.md`: Entity relationships and knowledge graphs.
- **Governing Architecture & ADRs**:
  - **ADR-0007: Domain-Driven Design Architecture**: Aggregate separation between NPCs and Establishments.
  - **ADR-0011: eventsource-py Core Event Sourcing**: Event-driven worker assignments and mood updates.

## Product & User Story References
- **Product Requirement**: [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- **User Story**: [`us-0073-customizable-establishments-and-assignable-npc-workers.md`](../../user_stories/accepted/us-0073-customizable-establishments-and-assignable-npc-workers.md)

## Detailed Specification & Implementation Plan
1. **Domain Events (`libs/runefoble_events/settlement_workers.py`)**:
   - `NPCWorkerAssigned`: `npc_id`, `establishment_id`, `role`, `wage`, `assigned_at`.
   - `NPCWorkerRelieved`: `npc_id`, `establishment_id`, `reason`.
   - `NPCMoodUpdated`: `npc_id`, `mood`, `temperament`, `patience_delta`.
   - `NPCRelationshipFormed`: `source_npc_id`, `target_npc_id`, `relation_type` (ally, rival, debtor, lover, mentor), `intensity`.
2. **Worker Aggregate & Graph Model**:
   - Track NPC Big Five personality traits, vices, and trade proficiencies.
   - Maintain shelf inventory (accessible to customers) versus backroom inventory (vault/secret goods).
   - Relationship adjacency list computing interpersonal tensions and supply chain dependencies.
3. **HTTP API**:
   - `POST /api/v1/establishments/{establishment_id}/workers`: Assign worker to role.
   - `GET /api/v1/establishments/{establishment_id}/workers`: Query active staff with inventories and relationships.
   - `PATCH /api/v1/npcs/{npc_id}/mood`: Update worker temperament state.

## Definition of Done
- Worker assignments correctly update establishment operations and projected service quality.
- Social relationships serialize to redstring-compatible graph edges.
- All source files strictly under 400 lines.
