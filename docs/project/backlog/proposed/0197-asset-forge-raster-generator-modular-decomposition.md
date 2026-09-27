---
id: '0197'
title: Asset Forge Raster Generator Modular Decomposition
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
target_release: 0.7.0
---

# TASK-0197: Asset Forge Raster Generator Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/asset_forge/src/asset_forge/generator.py` (330 lines, 66.0% of limit) into modular raster submodules under `services/asset_forge/src/asset_forge/raster/` (`png_codec.py`, `battlemap_raster.py`, and `token_raster.py`), keeping each submodule strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`services/asset_forge/src/asset_forge/generator.py` currently contains 330 lines combining low-level PNG binary chunk encoders (IHDR, IDAT, IEND, CRC32, scanline compression), procedural grid rasterization for dungeon/wilderness battlemaps, circular token portrait drawing, and printable papercraft standee generation. With upcoming 3D printable STL token and ring generation, this file will exceed 400 lines unless decoupled into focused raster modules.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean internal package structure for asset generation services.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain separation of low-level raster encoding from higher-level procedural map and token builders.
- **ADR-0010: Silo S3 Media Asset Bucket Storage**: Raster generation feeds directly into Silo S3 storage buckets.

## Scope of Work
1. **Modular Submodule Creation (`services/asset_forge/src/asset_forge/raster/`)**:
   - `png_codec.py`: Standard PNG chunk encoder (`encode_png_rgba`), scanline packing, CRC32 calculations, zlib compression, and hex color parsing (`parse_hex_color`) (< 90 lines).
   - `battlemap_raster.py`: Procedural tactical battlemap raster generator (`generate_battlemap_png`) with thematic color palettes and grid line overlays (< 110 lines).
   - `token_raster.py`: Circular token portrait generator (`generate_token_png`), border rings, and letter monograms (< 100 lines).
2. **Aggregator Facade (`services/asset_forge/src/asset_forge/generator.py`)**:
   - Maintain 100% backward-compatible function re-exports (`encode_png_rgba`, `parse_hex_color`, `generate_battlemap_png`, `generate_token_png`) (< 40 lines).
3. **Verification**:
   - Run `tests/test_blackbox_asset_forge_generation.py` to verify raster outputs remain identical.
   - Run `uv run pytest` and lint checks.

## Definition of Done
- `generator.py` reduced to a lightweight facade (< 50 lines).
- Submodules in `services/asset_forge/src/asset_forge/raster/` strictly < 120 lines each.
- All asset forge blackbox tests pass via `uv run pytest`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
