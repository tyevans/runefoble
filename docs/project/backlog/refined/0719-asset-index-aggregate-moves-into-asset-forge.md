---
id: '0719'
title: Asset Index Aggregate Moves Into Asset Forge
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0007
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: asset_forge
target_release: 0.9.0
---
# TASK-0719: Asset Index Aggregate Moves Into Asset Forge

## Status
Refined. Found by the refactor audit round r1 and checked against the code by the orchestrator.

## Summary
The platform lib owns an asset aggregate that only asset_forge uses. It imports `runefoble_events` without declaring the dependency.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/asset_index.py:35` defines `AssetIndexAggregate`. Lines 94-132 hold the repository functions.
- Only asset_forge uses it: `silo_upload.py:8`, `routers/wardrobe.py:12`, `routers/token.py:13`, `routers/battlemap.py:13`.
- `asset_index.py:16` imports `runefoble_events.asset`. `libs/runefoble_platform/pyproject.toml` does not list `runefoble-events`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0007, ADR-0011.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Move `asset_index.py` to `services/asset_forge/src/asset_forge/`. Update the four imports. Keep `storage.py` (the Silo port) in the platform lib.
2. Keep the uuid5 namespace and aggregate id derivation unchanged so stored events replay.
3. Remove the export from `runefoble_platform/__init__.py`. No alias remains.

## Frontdoor Blackbox Test Plan
- Upload, fetch and delete an asset through the asset_forge routes. A GET after delete returns 404.
- Replaying stored events gives the same aggregate ids as before the move.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `refactor-r1/libs.md`
