---
id: '0147'
title: Caravan Contracts API Router Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0129
- TASK-0146
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0006
- ADR-0011
governing_prds:
- PRD-0007
governing_stories:
- US-0058
target_release: 0.5.0
pr_url: https://github.com/tyevans/runefoble/pull/170
---
# TASK-0147: Caravan Contracts API Router Modular Decomposition

## Status
Refined

## Summary
Decompose `services/game_session/src/game_session/routers/caravan_contracts.py` (433 lines, 86.6% of limit) into modular sub-routers under `services/game_session/src/game_session/routers/caravan_contracts/` (`auth.py`, `board.py`, `lifecycle.py`, `__init__.py`), keeping all router modules < 180 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/routers/caravan_contracts.py` currently handles notice board posting, query filters, SpiceDB Zanzibar officer checks, contract acceptance, caravan dispatching, ambush reports, and settlement fulfillment in a single 433-line file. Decomposing it prevents imminent violation of Hard Invariant 6 (< 500 lines).

## Governing Architecture & ADRs
- **ADR-0001: Fine-Grained Authorization with SpiceDB Zanzibar**: Clean authorization helper extraction for party leader and officer permissions.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean router organization within `services/game_session/`.
- **ADR-0006: Redis Streams Event Bus Architecture**: Event dispatch across lifecycle transitions.
- **ADR-0011: eventsource-py Core Event Sourcing**: Event-sourced aggregate mutations.

## Product & User Story References
- **Product Requirement**: [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
- **User Story**: [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)

## Detailed Specification & Implementation Plan
1. **Authorization & Validation Helpers (`services/game_session/src/game_session/routers/caravan_contracts/auth.py`)**:
   - Extract `_to_uuid`, `_check_perm`, and `_check_high_tier_auth` (< 80 lines).
2. **Notice Board Router (`services/game_session/src/game_session/routers/caravan_contracts/board.py`)**:
   - Extract `POST /{shared_world_id}/contracts`, `GET /{shared_world_id}/contracts`, and `GET /{shared_world_id}/contracts/{contract_id}` (< 140 lines).
3. **Caravan Lifecycle Router (`services/game_session/src/game_session/routers/caravan_contracts/lifecycle.py`)**:
   - Extract `accept`, `dispatch`, `ambush`, `fulfill`, and `destroy` endpoints (< 170 lines).
4. **Aggregated Router Export (`services/game_session/src/game_session/routers/caravan_contracts/__init__.py`)**:
   - Combine sub-routers and export unified `router` preserving identical URL prefixes and tags (< 40 lines).
5. **Facade Backward Compatibility**:
   - `services/game_session/src/game_session/routers/caravan_contracts.py` re-exports `router` from package for existing imports (< 20 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Internal refactoring with zero change to public HTTP API endpoints or contracts.
- **Negotiable (N)**: Route split layout can be adjusted as long as files remain small.
- **Valuable (V)**: Protects against file size violations and improves readability of complex caravan state machines.
- **Estimable (E)**: Standard FastAPI router modularization.
- **Small (S)**: Bounded strictly to `services/game_session/src/game_session/routers/caravan_contracts/`; all files < 180 lines.
- **Testable (T)**: Validated by 100% pass rate in existing frontdoor blackbox test suites.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Architecture**:
   - `services/game_session/src/game_session/routers/caravan_contracts/` created with focused sub-routers.
   - All files strictly < 190 lines.
2. **Frontdoor Test Verification**:
   - `uv run pytest tests/test_blackbox_caravan_contracts/ tests/test_blackbox_west_marches/` passes with zero regressions.
3. **Quality Gates**:
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
