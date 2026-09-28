---
id: '0280'
title: Settlement Workers Router Modular Decomposition
status: Proposed
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
Proposed

## Summary
Decompose `services/game_session/src/game_session/settlement/workers_router.py` (358 lines, 71.6% of limit) into modular APIRouter submodules under `services/game_session/src/game_session/settlement/workers/` (`routes_roster.py`, `routes_relationships.py`, `routes_inventory.py`), ensuring all route modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/settlement/workers_router.py` handles HTTP endpoints for NPC worker creation, establishment assignments, social relationship queries (rivalries, debts, loyalties), and workplace inventory shelf management in a single 358-line file. As NPC daily schedules, payroll, and moral alignments are added, this file will breach the 500-line invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module structuring within bounded contexts.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
- **ADR-0013: Modular Microfrontend Decomposition**: Focused backend route modules backing UI subviews.

## Scope of Work
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

## Definition of Done
- `workers_router.py` reduced to strictly < 40 lines.
- Extracted route submodules strictly < 130 lines each.
- Passes all NPC worker test suites.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
