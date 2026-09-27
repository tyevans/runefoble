---
id: '0127'
title: West Marches Shared Persistent World State & Cross-Campaign Registry
status: Complete
created: 2026-09-26
dependencies:
- TASK-0008
- TASK-0010
- TASK-0047
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0011
governing_prds:
- PRD-0007
governing_stories:
- US-0058
target_release: 0.5.0
---
# TASK-0127: West Marches Shared Persistent World State & Cross-Campaign Registry

## Status
Refined

## Summary
Build multi-party shared world state synchronization, enabling separate adventuring campaigns to explore a common frontier, share discovery logs, establish regional trading outposts, and trade resources via cross-campaign ledgers with SpiceDB Zanzibar isolation.

## Problem Statement
Currently, each game session and campaign exists in a completely isolated silo (PRD-0007, US-0058). West Marches style play communities require shared geographical discoveries, merchant inventories that update when caravans travel between towns, and persistent communal bases.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object-Level Authorization**: Enforces multi-tenancy access control (`relation: participant`, `relation: guild_officer`).
- **ADR-0006: Redis Streams Event Bus**: Cross-campaign event broadcasting for `CrossCampaignDiscoveryShared` and `CaravanTradeCompleted`.
- **ADR-0011: eventsource-py Core Event Sourcing**: `SharedWorldAggregate` and `CaravanLedgerAggregate` managing persistent frontier state.

## Product & User Story References
- **Product Requirement**: [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
- **User Story**: [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)

## Detailed Specification & Implementation Plan
1. **Shared Frontier Domain Modeling (`services/game_session/src/game_session/west_marches.py`)**:
   - `SharedWorldAggregate` tracking common geographical map pins, shared stronghold levels, and communal tavern boards.
2. **Cross-Campaign Discovery Synchronization**:
   - When Party A maps a dungeon, Party B receives the discovery waypoint with discovery attribution metadata.
3. **Caravan Trade & Resource Ledger**:
   - Scheduled caravan transit delivering raw materials and crafted items between outposts, updating regional merchant stock.
4. **Zanzibar Security Scoping**:
   - Verifies that while world geography is shared, private character sheets and party whisper notes remain strictly isolated.
5. **Frontdoor Blackbox Verification**:
   - Blackbox test suite exercising cross-campaign public REST routes (`/api/v1/shared-worlds/{id}`) and verifying event propagation.

## INVEST Criteria Evaluation
- **Independent (I)**: Decoupled coordination layer over existing session and campaign lore aggregates.
- **Negotiable (N)**: Caravan travel timer intervals (real-world hours vs session turns) can be configured.
- **Valuable (V)**: Unlocks scalable, multi-party community tabletop gaming.
- **Estimable (E)**: Builds on existing Redis Streams event streaming and PostgreSQL event store.
- **Small (S)**: Scope strictly isolated to `services/game_session/`; all files < 320 lines.
- **Testable (T)**: Tested with multi-campaign fixtures asserting shared discovery state and access boundaries.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Shared World Aggregates**:
   - `SharedWorldAggregate` in `services/game_session/` handling cross-party discoveries and caravan trading ledgers.
2. **SpiceDB Multi-Party Scoping**:
   - Verified that unshared party secrets cannot be accessed by external party members.
3. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_west_marches.py` verifying multi-campaign discovery synchronization and trading ledger updates via public HTTP endpoints.
4. **Quality Gates**:
   - Conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run pytest tests/test_blackbox_west_marches.py`.
