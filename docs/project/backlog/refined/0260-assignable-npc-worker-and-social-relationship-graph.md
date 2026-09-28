---
id: '0260'
title: Assignable NPC Worker Engine and Social Relationship Graph
status: Refined
created: 2026-09-27
dependencies:
- TASK-0259
governing_adrs:
- ADR-0001
- ADR-0002
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
Refined

## Summary
Build the worker management and social relationship graph subsystem for establishments, enabling NPCs to be assigned to roles (head baker, armorer, croupier, bouncer, apprentice) with distinct personality traits, dynamic inventories, memory of town events, and interconnected interpersonal ties.

## Problem Statement
Town establishments currently lack living staff. Merchants are stateless entities with static compendium price lists rather than dynamic NPCs with wages, morale, vendor margins, personal loyalties, or interpersonal rivalries that react to player deeds and regional events.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/simulate-npc-faction-agendas-and-world-ticks.md`: NPC faction agendas and autonomous background simulation ticks.
  - `docs/how-to/index-campaign-lore-with-redstring.md`: Entity relationships and knowledge graphs.
  - `docs/how-to/define-event-sourced-aggregates.md`: Declarative aggregate state mutations.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Campaign member authority to hire and direct town workers.
  - **ADR-0002: Domain Events via eventsource-py**: Immutable event audit log of worker hiring, firing, and mood shifts.
  - **ADR-0007: Domain-Driven Design Architecture**: Aggregate separation between NPCs and Establishments.
  - **ADR-0011: PostgreSQL Event Store**: Event stream persistence and projection hydration.

## Product & User Story References
- **Product Requirement**: [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- **User Story**: [`us-0073-customizable-establishments-and-assignable-npc-workers.md`](../../user_stories/accepted/us-0073-customizable-establishments-and-assignable-npc-workers.md)

## Detailed Specification & Implementation Plan
1. **Domain Events (`libs/runefoble_events/settlement_workers.py`)**:
   - `NPCWorkerAssigned`: `npc_id`, `establishment_id`, `role`, `wage`, `assigned_at`.
   - `NPCWorkerRelieved`: `npc_id`, `establishment_id`, `reason`.
   - `NPCMoodUpdated`: `npc_id`, `mood`, `temperament`, `patience_delta`.
   - `NPCRelationshipFormed`: `source_npc_id`, `target_npc_id`, `relation_type` (ally, rival, debtor, lover, mentor), `intensity`.
2. **Worker Aggregate & Graph Model (`services/game_session/src/game_session/settlement/workers.py`)**:
   - Track NPC Big Five personality traits, vices, and trade proficiencies.
   - Maintain shelf inventory (accessible to customers) versus backroom inventory (vault/secret goods).
   - Relationship adjacency list computing interpersonal tensions and supply chain dependencies.
3. **HTTP API**:
   - `POST /api/v1/establishments/{establishment_id}/workers`: Assign worker to role.
   - `GET /api/v1/establishments/{establishment_id}/workers`: Query active staff with inventories and relationships.
   - `PATCH /api/v1/npcs/{npc_id}/mood`: Update worker temperament state.
4. **Frontdoor Blackbox Verification (`tests/test_blackbox_npc_worker_engine.py`)**:
   - Assign worker via frontdoor API, assert worker shows up in establishment roster.
   - Update worker mood, assert temperament projection reflects change.

## INVEST Criteria Evaluation
- **Independent (I)**: Depends solely on `TASK-0259` settlement model and core events library.
- **Negotiable (N)**: Number of personality facets and relationship intensities can be tuned.
- **Valuable (V)**: Transforms static shops into living roleplay hubs with memorable NPC staff.
- **Estimable (E)**: Event models and social graph adjacency list sized for a single sprint pass.
- **Small (S)**: Kept under 300 lines per module.
- **Testable (T)**: Frontdoor API calls return clear JSON projections and emit CloudEvents.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Worker assignments correctly update establishment operations and projected service quality.
2. Social relationships serialize to redstring-compatible graph edges.
3. HTTP routes allow assigning staff and retrieving worker rosters with permissions.
4. Blackbox frontdoor tests pass via `uv run pytest tests/test_blackbox_npc_worker_engine.py`.
5. All source files strictly under 400 lines per `AGENTS.md` Rule 6.
