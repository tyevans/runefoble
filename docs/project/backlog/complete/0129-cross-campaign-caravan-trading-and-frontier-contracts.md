---
id: 0129
title: Cross-Campaign Caravan Trading Ledgers & Frontier Mercenary Contracts
status: Complete
created: 2026-09-26
dependencies:
- TASK-0008
- TASK-0010
- TASK-0047
- TASK-0127
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0011
- ADR-0013
governing_prds:
- PRD-0007
governing_stories:
- US-0058
target_release: 0.5.0
pr_url: https://github.com/tyevans/runefoble/pull/147
---
# TASK-0129: Cross-Campaign Caravan Trading Ledgers & Frontier Mercenary Contracts

## Status
Refined

## Summary
Expand West Marches community play by introducing asynchronous mercenary contracts and caravan trading ledgers, allowing adventuring parties across separate campaigns to post bounties, escort merchant caravans, trade regional supplies, and resolve frontier economic dependencies with SpiceDB Zanzibar multi-tenancy authorization.

## Problem Statement
While shared frontier discovery is enabled by TASK-0127, parties still lack structured economic and narrative interdependence across campaigns (PRD-0007, US-0058). Guild masters and DMs need an asynchronous bounty and caravan escort system where Party A can fund a supply caravan between regional strongholds and Party B can accept the contract to escort or defend it during their live session.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object-Level Authorization**: Enforces fine-grained access control on contract postings (`relation: poster`, `relation: contractor`, `relation: guild_officer`).
- **ADR-0006: Redis Streams Event Bus**: Event dispatch and cross-campaign broadcasting for `CaravanContractPosted`, `CaravanDispatched`, `CaravanAmbushed`, and `CaravanTradeFulfilled`.
- **ADR-0011: eventsource-py Core Event Sourcing**: `CaravanContractAggregate` managing contract lifecycle, cargo value, route risk, escort payouts, and destination settlement delivery.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Caravan trading board and contract manifest UI components in `services/game_session/ui/src/`.

## Product & User Story References
- **Product Requirement**: [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
- **User Story**: [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)

## Detailed Specification & Implementation Plan
1. **Caravan Manifest & Contract Domain Modeling (`services/game_session/src/game_session/caravan.py`)**:
   - `CaravanContractAggregate` modeling cargo inventory, route risk level, transit stages, escort collateral, and reward gold/reputation.
   - Declarative command handlers for `post_contract`, `accept_contract`, `dispatch_caravan`, `report_ambush_outcome`, and `fulfill_contract`.
2. **Asynchronous Multi-Party Notice Board**:
   - Public REST endpoints (`/api/v1/shared-worlds/{world_id}/caravans/contracts`) for browsing available merchant contracts across campaigns.
   - Outpost board queries filtering by risk level, destination settlement, and expiration turns.
3. **Dynamic Settlement Economy & Merchant Stock Sync**:
   - Event subscriber updating destination settlement merchant inventory and reagent supplies when a caravan arrives safely.
   - Economic price modifier calculation based on recent caravan delivery success rates.
4. **SpiceDB Zanzibar Authorization**:
   - Schema relations enforcing that only party leaders or guild officers can bind party funds or accept high-tier mercenary contracts.
5. **Frontdoor Blackbox Verification**:
   - Blackbox test suite verifying contract posting, multi-campaign acceptance, event streaming over Redis, and economic payout settlement.

## INVEST Criteria Evaluation
- **Independent (I)**: Decoupled contract aggregate layered on top of shared world state (TASK-0127) without mutating active turn order.
- **Negotiable (N)**: Caravan travel stages and hazard mishap probabilities can be configured per outpost route.
- **Valuable (V)**: Drives persistent, collaborative living-world storytelling across multiple disparate gaming groups.
- **Estimable (E)**: Follows standard `eventsource-py` aggregate patterns and FastAPI APIRouter structures.
- **Small (S)**: Scope strictly isolated to `services/game_session/` and `libs/runefoble_events/`; all files < 320 lines.
- **Testable (T)**: Frontdoor REST API and CloudEvents tests verify contract state machine and payout mechanics.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Caravan Contract Aggregate**:
   - `CaravanContractAggregate` implemented with full `@handles` event handlers for all lifecycle stages.
2. **REST API Routes**:
   - Public HTTP endpoints for posting, claiming, and fulfilling caravan contracts with SpiceDB permission checks.
3. **Domain Event Registration**:
   - CloudEvents registered with `@register_event` for `CaravanContractPosted`, `CaravanDispatched`, and `CaravanTradeFulfilled`.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_caravan_contracts.py` verifying full contract lifecycle and event emission through public endpoints.
5. **Quality Gates**:
   - Conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run pytest tests/test_blackbox_caravan_contracts.py` and `uv run ruff check .`.
