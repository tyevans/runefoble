---
id: '0164'
title: Cross-Campaign Settlement and Haven Registry
status: Complete
created: 2026-09-26
dependencies:
- TASK-0127
- TASK-0129
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0018
governing_stories:
- US-0058
target_release: 0.7.0
pr_url: https://github.com/tyevans/runefoble/pull/194
---
# TASK-0164: Cross-Campaign Settlement and Haven Registry

## Status
Refined

## Summary
Implement persistent multi-campaign settlement and outpost storage in `services/game_session/`, exposing REST endpoints for charting communal havens, workshops, and resting sanctums across West Marches campaigns with SpiceDB Zanzibar isolation.

## Problem Statement
Outposts founded or liberated by one adventuring party currently remain invisible to other parties exploring the same frontier wilderness, preventing shared settlement infrastructure and cross-party community building.

## Governing Architecture & ADRs
- **ADR-0001: Zanzibar Fine-Grained Authorization with SpiceDB**: Cross-campaign access scopes and haven discovery relationships.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module boundaries in `services/game_session/`.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Shared haven state notifications across campaign streams.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for settlement progression.
- **ADR-0011: PostgreSQL Event Store via Eventsource-py**: DeclarativeAggregate for settlement lifecycle.

## Product & User Story References
- **Product Requirement**: [`prd-0018-west-marches-shared-world-and-caravans.md`](../../product/accepted/prd-0018-west-marches-shared-world-and-caravans.md)
- **User Story**: [`us-0058-west-marches-shared-world-and-cross-campaign-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-and-cross-campaign-trade.md)

## Detailed Specification & Implementation Plan
1. **Settlement Aggregate & Models (`services/game_session/src/game_session/settlements/aggregate.py`)**:
   - Pydantic models and DeclarativeAggregate for outposts, fortresses, defensive fortifications, and workshop tiers (< 150 lines).
2. **SpiceDB Haven Permissions (`services/game_session/src/game_session/settlements/auth.py`)**:
   - Check and write Zanzibar relations for campaign discovery and settlement access (< 110 lines).
3. **CloudEvents Registration (`libs/runefoble_events/src/runefoble_events/settlements.py`)**:
   - Define `SettlementCharteredEvent`, `SettlementUpgradedEvent`, and `SettlementRestBoonClaimedEvent` (< 90 lines).
4. **FastMCP Tool & REST API (`services/game_session/src/game_session/routers/settlements.py`)**:
   - `POST /settlements`: Charter new frontier settlement.
   - `GET /settlements/{settlement_id}`: Query settlement status and available facilities.
   - `POST /settlements/{settlement_id}/upgrade`: Upgrade facility tier (< 140 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Supplements West Marches world state without breaking individual session gameplay.
- **Negotiable (N)**: Haven upgrade costs and facility tier limits can be balanced.
- **Valuable (V)**: Enables true shared-world persistent civilization building across multiple gaming groups.
- **Estimable (E)**: Standard event-sourced aggregate and SpiceDB relation checks.
- **Small (S)**: Bounded strictly to `services/game_session/src/game_session/settlements/`; all files < 160 lines.
- **Testable (T)**: Frontdoor blackbox tests verify REST endpoints, SpiceDB access rules, and CloudEvents.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Domain Engine & Handlers**:
   - `services/game_session/src/game_session/settlements/` created with focused submodules.
   - All modules strictly < 160 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_settlements/` verifies chartering, facility upgrading, and multi-campaign visibility.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_settlements/`, `uv run ruff check .`, and `uv run ruff format --check .`.
