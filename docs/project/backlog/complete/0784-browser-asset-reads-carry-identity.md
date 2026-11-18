---
id: '0784'
title: Browser Asset Reads Carry Identity
status: Complete
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

# TASK-0784: Browser Asset Reads Carry Identity

## Status
Complete

## Summary
Asset reads now need a bearer and `forged_asset.view`. A browser `<img src>` or `<a href>` cannot send a bearer header, so any UI that renders an asset URL directly cannot show the asset.

## Problem Statement
- `services/board_state/ui/src/runefoble-map-dropzone.ts:75` keeps `download_url` for display.
- `services/asset_forge/ui/src/runefoble-print-forge.ts:174` links to `download_url`.
- Check every UI use of an asset URL in `frontend/src` and `services/*/ui/src`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0001, ADR-0015.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Choose one approach and record it in `docs/reference/service-client.md` or a new reference page: a fetch with the shared bearer helper into a blob URL, or a short-lived signed URL that asset_forge issues after a `forged_asset.view` check.
2. Update each UI use to the chosen approach.

## Frontdoor Blackbox Test Plan
- A Storybook story shows an uploaded asset through the chosen path with zero console errors.
- A stranger cannot use a URL issued to another user after it expires (if signed URLs are chosen).

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: Batch 23 gate fix, orchestrator (asset read authorization)
