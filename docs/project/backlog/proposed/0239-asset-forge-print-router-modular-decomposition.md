---
id: '0239'
title: Asset Forge Print Forge Router Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0049
- TASK-0105
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0010
governing_prds:
- PRD-0009
- PRD-0015
governing_stories:
- US-0021
- US-0049
target_release: 0.8.0
---

# TASK-0239: Asset Forge Print Forge Router Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/asset_forge/src/asset_forge/routers/print_forge.py` (303 lines, 60.6% of limit) into modular sub-routers under `services/asset_forge/src/asset_forge/routers/print/` (`pdf_routes.py`, `standees_routes.py`, `stl_routes.py`), keeping each route module strictly < 110 lines per Hard Invariant 6 and ADR-0003/ADR-0007.

## Problem Statement
`services/asset_forge/src/asset_forge/routers/print_forge.py` spans 303 lines implementing grid-calibrated multi-page PDF generation, papercraft standees export, and 3D STL token mesh manufacturing in a single router file. As new physical asset templates and status clip rings are added, this router approaches the warning threshold unless decomposed into modular route handlers.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean router organization within service packages.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation between 2D printouts and 3D physical fabrication.
- **ADR-0010: Silo S3 Media Asset Bucket Storage**: Unified storage upload dependencies and signed URLs.

## Scope of Work
1. **Modular Route Sub-Modules (`services/asset_forge/src/asset_forge/routers/print/`)**:
   - `pdf_routes.py`: Battlemap PDF tiling routes (`/assets/print-pdf`, `/api/v1/forge/print-pdf`) (< 90 lines).
   - `standees_routes.py`: Foldable papercraft standees PDF generation routes (`/assets/standees`, `/api/v1/forge/standees`) (< 90 lines).
   - `stl_routes.py`: 3D STL token and base mesh generation routes (`/assets/stl-token`, `/api/v1/forge/stl-token`) (< 95 lines).
2. **Aggregator Router Facade (`services/asset_forge/src/asset_forge/routers/print_forge.py`)**:
   - Aggregate sub-routers under unified `router = APIRouter(tags=["Print Forge"])` preserving 100% backward-compatible route URLs (< 40 lines).
3. **Verification**:
   - Run blackbox tests in `tests/test_blackbox_printable_forge.py` and ensure all endpoints respond correctly.
   - Run `uv run pytest tests/test_blackbox_printable_forge.py` and lint checks.

## Definition of Done
- `print_forge.py` decomposed into modular sub-routers strictly < 110 lines each.
- All PDF, standee, and STL routes preserve exact paths and responses.
- Passes `uv run pytest tests/test_blackbox_printable_forge.py`.
- Passes `uv run ruff check .` and `uv run ruff format --check .`.
