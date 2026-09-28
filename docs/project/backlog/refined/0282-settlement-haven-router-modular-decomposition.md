---
id: '0282'
title: Settlement Haven Router Modular Decomposition
status: Refined
created: 2026-09-28
dependencies:
- TASK-0259
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0072
target_release: 0.8.0
---

# TASK-0282: Settlement Haven Router Modular Decomposition

## Status
Refined

## Summary
Decompose `services/game_session/src/game_session/settlement/router.py` (351 lines, 70.2% of limit) into modular APIRouter submodules under `services/game_session/src/game_session/settlement/haven/` (`routes_havens.py`, `routes_establishments.py`, `routes_upgrades.py`), ensuring all route modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/settlement/router.py` manages endpoints for haven chartering, spatial tier scaling (hamlet to metropolis), establishment zoning, facility construction, and civic upgrades in a single 351-line file. As economic trade routes and defensive siege fortifications are introduced, this file will breach the 500-line invariant unless decomposed into dedicated route submodules.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/charter-frontier-settlements-and-havens.md`: Haven lifecycle, establishment zoning, and civic upgrades.
  - `docs/how-to/decompose-microservice-routers.md`: Splitting large FastAPI routers into modular APIRouter packages.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Haven permission enforcement on route endpoints.
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout within the bounded context.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.
  - **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 130 lines).

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
  - [`us-0072-mobile-responsive-settlement-browser-and-town-builder.md`](../../user_stories/accepted/us-0072-mobile-responsive-settlement-browser-and-town-builder.md)

## Detailed Specification & Implementation Plan
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

## INVEST Criteria Evaluation
- **Independent (I)**: Internal router refactoring without changing HTTP contracts or database schemas.
- **Negotiable (N)**: Sub-router categorization can be adjusted.
- **Valuable (V)**: Protects haven router from breaching the 500-line invariant limit.
- **Estimable (E)**: Pure extraction of route handlers into modular APIRouters.
- **Small (S)**: Each extracted router module strictly < 130 lines.
- **Testable (T)**: Frontdoor API verification in `tests/test_blackbox_settlements_integration.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `services/game_session/src/game_session/settlement/router.py` reduced to strictly < 40 lines.
2. Extracted route submodules strictly < 130 lines each per Hard Invariant 6.
3. 100% route contract and status code parity preserved.
4. Passes all settlement haven test suites via `uv run pytest tests/test_blackbox_settlements_integration.py`.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
