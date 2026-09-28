---
id: '0198'
title: Campaign Lore Codex Router Modular Decomposition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0106
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds:
- PRD-0015
governing_stories:
- US-0050
target_release: 0.7.0
---

# TASK-0198: Campaign Lore Codex Router Modular Decomposition

## Status
Refined

## Summary
Decompose `services/campaign_lore/src/campaign_lore/routers/codex.py` (325 lines, 65.0% of limit) into modular submodules under `services/campaign_lore/src/campaign_lore/routers/codex/` (`schemas.py`, `entries.py`, and `referencing.py`), keeping each submodule strictly < 120 lines per Hard Invariant 6 and ADR-0003/ADR-0007.

## Problem Statement
`services/campaign_lore/src/campaign_lore/routers/codex.py` currently contains 325 lines mixing Pydantic request models (`PublishCodexEntryRequest`, `UpdateCodexEntryRequest`), entry CRUD routing (`publish_entry`, `get_entry`, `update_entry`), and cross-reference analysis (`get_entry_references`, entity link extraction). As persistent West Marches settlements and shared discovery logs expand codex capabilities, this router will approach the 400-line warning threshold unless decoupled into focused sub-components.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean internal package layout for microservice bounded contexts.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation between API serialization, aggregate orchestration, and cross-referencing logic.

## Detailed Specification & Implementation Plan
1. **Modular Submodule Creation (`services/campaign_lore/src/campaign_lore/routers/codex/`)**:
   - `schemas.py`: Pydantic request and response schemas for codex publishing, updates, and cross-referencing payloads (< 80 lines).
   - `entries.py`: REST endpoints for entry publishing, retrieval, update, and search filtering (< 110 lines).
   - `referencing.py`: Cross-referencing, entity link extraction, and mention resolution endpoints (< 100 lines).
2. **Aggregator Router (`services/campaign_lore/src/campaign_lore/routers/codex.py`)**:
   - Export unified `router = APIRouter(...)` retaining exact routes and backward compatibility (< 50 lines).
3. **Verification**:
   - Run existing blackbox tests in `tests/test_blackbox_campaign_atlas.py` and codex tests.
   - Run `uv run pytest` and lint checks.

## INVEST Criteria Evaluation
- **Independent (I)**: Router decomposition is self-contained within `campaign_lore` router hierarchy.
- **Negotiable (N)**: Logical submodules separate schemas, CRUD operations, and cross-reference analysis.
- **Valuable (V)**: Protects against Hard Invariant 6 and clarifies codex API endpoints.
- **Estimable (E)**: Standard FastAPI router decomposition with clear route mapping.
- **Small (S)**: Scope strictly isolated to `codex.py` refactoring (< 120 lines per submodule).
- **Testable (T)**: Frontdoor verification via HTTP client calls against existing codex endpoints.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `codex.py` decomposed into focused submodules strictly < 120 lines each.
   - Aggregator facade retains exact router tags and paths (< 50 lines).
2. **Frontdoor Verification**:
   - All codex API routes continue to function identically with zero regression.
   - All tests pass via `uv run pytest tests/test_blackbox_campaign_atlas.py`.
3. **Quality Gates**:
   - Linting passes via `uv run ruff check .` and `uv run ruff format --check .`.
