---
id: '0280'
title: Settlement Workers Router Modular Decomposition
status: Refined
created: 2026-09-28
dependencies:
- TASK-0260
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0073
target_release: 0.8.0
---

# TASK-0280: Settlement Workers Router Modular Decomposition

## Status
Refined

## Summary
Decompose `services/game_session/src/game_session/settlement/workers_router.py` (358 lines, 71.6% of limit) into modular APIRouter submodules under `services/game_session/src/game_session/settlement/workers/` (`routes_roster.py`, `routes_relationships.py`, `routes_inventory.py`), ensuring all route modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/settlement/workers_router.py` handles HTTP endpoints for NPC worker creation, establishment assignments, social relationship queries (rivalries, debts, loyalties), and workplace inventory shelf management in a single 358-line file. As NPC daily schedules, payroll, and moral alignments are added, this file will breach the 500-line invariant unless decomposed into dedicated APIRouters.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/decompose-microservice-routers.md`: Decomposing monolithic FastAPI microservices into modular APIRouters.
  - `docs/how-to/build-settlements-and-play-mobile-minigames.md`: Living NPC worker assignment, relationships, and inventory shelves.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout within the `game_session` service.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
  - **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 130 lines).

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
  - [`us-0073-customizable-establishments-and-assignable-npc-workers.md`](../../user_stories/accepted/us-0073-customizable-establishments-and-assignable-npc-workers.md)

## Detailed Specification & Implementation Plan
1. **Worker Roster & Assignment Routes (`services/game_session/src/game_session/settlement/workers/routes_roster.py`)**:
   - Extract worker creation, listing, status updates, and establishment reassignment endpoints (< 120 lines).
2. **Social Relationships & Rumors Routes (`services/game_session/src/game_session/settlement/workers/routes_relationships.py`)**:
   - Extract relationship graph queries, loyalty modifications, and workplace rumor discovery (< 110 lines).
3. **Workplace Shelf Inventory Routes (`services/game_session/src/game_session/settlement/workers/routes_inventory.py`)**:
   - Extract shop inventory listings, item price lookups, restock endpoints, and vault access (< 110 lines).
4. **Aggregator Router (`services/game_session/src/game_session/settlement/workers_router.py`)**:
   - Combine sub-routers with clean prefix and tag mappings (< 35 lines).
5. **Verification**:
   - Run worker engine tests to confirm all endpoint contracts and status codes are preserved.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal route restructuring preserving identical HTTP paths, schemas, and responses.
- **Negotiable (N)**: Route groupings can be adjusted as long as files remain < 130 lines.
- **Valuable (V)**: Protects worker routes file from exceeding the 500-line invariant.
- **Estimable (E)**: Pure extraction of endpoint handlers and routing decorators.
- **Small (S)**: Each extracted router module strictly < 130 lines.
- **Testable (T)**: Frontdoor API tests in `tests/test_blackbox_settlements_integration.py` verify full endpoint functionality.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `services/game_session/src/game_session/settlement/workers_router.py` reduced to strictly < 40 lines.
2. Extracted route submodules strictly < 130 lines each per Hard Invariant 6.
3. 100% route compatibility and OpenAPI schema parity preserved.
4. Passes all NPC worker test suites via `uv run pytest tests/test_blackbox_settlements_integration.py`.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
