---
id: '0785'
title: Forged Asset Links Are Signed and Checked Before Reading
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: asset_forge
target_release: 0.9.0
---

# TASK-0785: Forged Asset Links Are Signed and Checked Before Reading

## Status
Refined. Found during batch 23 integration, 2026-11-17.

## Summary
Print forge and forged-image responses return plain Silo object URLs. The `?expires=3600` query is not a signature, so anyone who has a link can read the object with no permission check.

## Problem Statement
- `services/asset_forge/src/asset_forge/routers/print_forge.py:108-309`: responses carry raw object URLs.
- `libs/runefoble_platform/src/runefoble_platform/storage.py:107`: builds the URL with an unsigned `expires` query.
- `services/asset_forge/ui/src/runefoble-print-forge.ts:174`: the export link uses that URL.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0001, ADR-0015.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Forged outputs become `forged_asset` records with a creator tuple, as uploads do.
2. Responses return the asset id and an `/api/v1/assets/{id}` path. Reads go through the `forged_asset.view` check from commit 8224d8f0.
3. If a direct Silo link is still needed, issue a real presigned URL with a short lifetime only after the view check. Remove the unsigned `expires` builder.
4. The print forge UI downloads through the shared bearer helper into a blob URL, as `runefoble-map-dropzone` does (TASK-0784).

## Frontdoor Blackbox Test Plan
- A forged PDF, standee or STL is readable by its creator and refused (403) for a stranger.
- No response body holds an unsigned Silo object URL.
- Storybook story for the print forge downloads through the blob path with zero console errors.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `.audit/work/0784.md` (Discovered)
