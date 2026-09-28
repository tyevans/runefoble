---
id: '0302'
title: Campaign Lore Atlas Router Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0106
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0015
governing_stories:
- US-0050
target_release: 0.8.0
---

# TASK-0302: Campaign Lore Atlas Router Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/campaign_lore/src/campaign_lore/routers/atlas.py` (298 lines, 59.6% of limit) into modular sub-routers under `services/campaign_lore/src/campaign_lore/routers/atlas/` (`pins.py`, `territories.py`, `layers.py`, `schemas.py`, `__init__.py`), keeping each submodule strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`services/campaign_lore/src/campaign_lore/routers/atlas.py` currently bundles multiple disparate responsibilities into a single 298-line router:
1. Pydantic request models (`CreatePinRequest`, `ToggleLayerRequest`, `DefineTerritoryRequest`).
2. Milestone pin lifecycle operations (placement, deletion, linked entity metadata).
3. Territory definition, containment queries, and contested boundary detection.
4. Layer visibility toggling and coordinate projection endpoints.

As deep-zoom multi-era maps, contested zone border skirmishes, and tactical fog integration evolve, this router will rapidly approach the 500-line invariant limit unless partitioned into focused sub-routers.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular sub-packages within services.
- **ADR-0007: Domain-Driven Design Architecture**: Clear separation of geographical entities and routes.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 100 lines).

## Scope of Work
1. **Request & Response Schemas (`services/campaign_lore/src/campaign_lore/routers/atlas/schemas.py`)**:
   - Extract `CreatePinRequest`, `ToggleLayerRequest`, and `DefineTerritoryRequest` (< 50 lines).
2. **Milestone Pins Router (`services/campaign_lore/src/campaign_lore/routers/atlas/pins.py`)**:
   - Extract pin placement, retrieval, and deletion endpoints (< 90 lines).
3. **Territories & Boundaries Router (`services/campaign_lore/src/campaign_lore/routers/atlas/territories.py`)**:
   - Extract territory definition, query, and contested zone detection endpoints (< 90 lines).
4. **Layers & Projection Router (`services/campaign_lore/src/campaign_lore/routers/atlas/layers.py`)**:
   - Extract layer toggle and coordinate projection endpoints (< 60 lines).
5. **Main Atlas APIRouter Facade (`services/campaign_lore/src/campaign_lore/routers/atlas/__init__.py`)**:
   - Compose sub-routers into the unified `router = APIRouter(prefix="/api/v1/campaigns/{campaign_id}/atlas", tags=["Campaign Atlas"])` (< 35 lines).
6. **Verification**:
   - Run `uv run pytest tests/test_blackbox_campaign_atlas*.py` to ensure zero route regression.

## Definition of Done
- `services/campaign_lore/src/campaign_lore/routers/atlas.py` converted into modular `atlas/` sub-package.
- Each extracted submodule strictly < 100 lines per Hard Invariant 6.
- 100% route contract and URL prefix backwards compatibility preserved.
- All campaign atlas blackbox tests pass cleanly.
