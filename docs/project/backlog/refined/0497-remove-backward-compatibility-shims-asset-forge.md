---
id: '0497'
title: Remove Backward Compatibility Shims & Re-exports in asset_forge
status: Refined
created: 2026-09-29
dependencies:
- TASK-0023
- TASK-0031
governing_adrs:
- ADR-0003
- ADR-0005
- ADR-0013
governing_prds:
- PRD-0009
governing_stories:
- US-0009
- US-0026
target_release: 0.9.0
---

# TASK-0497: Remove Backward Compatibility Shims & Re-exports in asset_forge

## Status
Refined

## Summary
Decommission backward-compatibility aggregator facades (`src/asset_forge/generator.py`), excise legacy function aliases (`generate_token_avatar = generate_token_portrait` in `raster/token_raster.py`), and migrate all raster and battlemap synthesis callers directly to modular subpackages in `asset_forge.raster.*`.

## Problem Statement
In `services/asset_forge`:
- `src/asset_forge/generator.py` is a 25-line aggregator facade explicitly documented as `"""Aggregator facade re-exporting procedural raster generators for backward compatibility."""`
- `src/asset_forge/raster/token_raster.py` contains `# Backward compatibility alias` (`generate_token_avatar = generate_token_portrait`).
These legacy artifacts exist only to prevent breakage for older callers, which violates the zero backward compatibility DoR rule.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/forge-procedural-battlemaps-and-tokens.md`: Procedural battlemaps and token avatar generation.
  - `docs/reference/ports-and-endpoints.md`: Asset forge port 8009.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace**: Monorepo package boundaries.
  - **ADR-0005: Silo S3 Storage Pipeline**: Media asset bucket storage.
  - **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend component vendoring.

## Product & User Story References
- [`prd-0009-campfire-crafting-and-resting-boons.md`](../../product/accepted/prd-0009-campfire-crafting-and-resting-boons.md)
- [`us-0026-procedural-battlemap-synthesis.md`](../../user_stories/accepted/us-0026-procedural-battlemap-synthesis.md)

## Detailed Specification & Implementation Plan
1. **Delete Aggregator Facade**:
   - Delete `services/asset_forge/src/asset_forge/generator.py`.
   - Update callers to import generators directly from `asset_forge.raster.map_raster`, `asset_forge.raster.token_raster`, or `asset_forge.diffusion.*`.
2. **Remove Function Aliases**:
   - In `services/asset_forge/src/asset_forge/raster/token_raster.py`, remove the `generate_token_avatar = generate_token_portrait` alias.
   - Update any callers to invoke `generate_token_portrait` directly.
3. **Clean Up `asset_forge/__init__.py`**:
   - Prune package root exports, ensuring only authoritative generators and models are exposed.
4. **Update Blackbox Test Suites**:
   - Verify tests in `tests/test_asset_forge*` pass without references to `generator.py` or `generate_token_avatar`.

## INVEST Criteria Evaluation
- **Independent (I)**: Changes are strictly self-contained within `services/asset_forge`.
- **Negotiable (N)**: Clean standard Python modular imports.
- **Valuable (V)**: Removes redundant generator facade and eliminates ambiguous function aliases.
- **Estimable (E)**: Bounded to `generator.py`, `token_raster.py`, and direct callers.
- **Small (S)**: File changes well under 50 lines.
- **Testable (T)**: Verified via `uv run pytest tests/test_asset_forge*`.

## Definition of Done
1. `generator.py` facade deleted.
2. `generate_token_avatar` alias removed from `token_raster.py`.
3. All callers across asset forge and tests migrated to canonical submodules.
4. All asset forge tests pass cleanly.
