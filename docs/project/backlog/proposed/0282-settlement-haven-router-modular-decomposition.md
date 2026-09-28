---
id: '0282'
title: Settlement Haven Router Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0259
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0007
governing_prds:
- PRD-0024
governing_stories:
- US-0072
target_release: 0.8.0
---

# TASK-0282: Settlement Haven Router Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/src/game_session/settlement/router.py` (351 lines, 70.2% of limit) into modular APIRouter submodules under `services/game_session/src/game_session/settlement/haven/` (`routes_havens.py`, `routes_establishments.py`, `routes_upgrades.py`), ensuring all route modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/settlement/router.py` manages endpoints for haven chartering, spatial tier scaling (hamlet to metropolis), establishment zoning, facility construction, and civic upgrades in a single 351-line file. As economic trade routes and defensive siege fortifications are introduced, this file will breach the 500-line invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Haven permission enforcement.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module boundaries within bounded contexts.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.

## Scope of Work
1. **Haven Lifecycle Routes (`services/game_session/src/game_session/settlement/haven/routes_havens.py`)**:
   - Extract haven creation, listing, tier scaling, and metadata endpoints (< 110 lines).
2. **Establishment Zoning Routes (`services/game_session/src/game_session/settlement/haven/routes_establishments.py`)**:
   - Extract building creation, zoning classifications (hospitality, commerce, faith), and district assignments (< 120 lines).
3. **Civic Upgrades & Facilities Routes (`services/game_session/src/game_session/settlement/haven/routes_upgrades.py`)**:
   - Extract facility upgrades, prosperity calculations, and defense rating modifiers (< 110 lines).
4. **Aggregator Router (`services/game_session/src/game_session/settlement/router.py`)**:
   - Combine sub-routers with clean prefix and tag mappings (< 35 lines).
5. **Verification**:
   - Run haven blackbox tests to confirm endpoint routing and payload schema parity.

## Definition of Done
- `router.py` reduced to strictly < 40 lines.
- Extracted route submodules strictly < 130 lines each.
- Passes all settlement haven test suites.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
