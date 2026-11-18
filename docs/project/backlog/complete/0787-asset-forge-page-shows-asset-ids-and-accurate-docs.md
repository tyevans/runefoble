---
id: '0787'
title: Asset Forge Page Shows Generated Asset IDs and the Forge Docs Match the Components
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0013
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: asset_forge
target_release: 0.9.0
---

# TASK-0787: Asset Forge Page Shows Generated Asset IDs and the Forge Docs Match the Components

## Status
Complete

## Summary
The App Shell forge page (TASK-0645) shows no asset id after generation, and the preview URL form is not done. One e2e feature still uses the removed `#/forge` path. A how-to names the wrong uploader input.

## Problem Statement
- `services/asset_forge/ui/src/`: `<runefoble-asset-forge>` renders no asset id.
- `e2e/features/asset_forge.feature`: navigates to `#/forge`. The route is `#/campaigns/:campaignId/forge`.
- `docs/how-to/forge-procedural-battlemaps-and-tokens.md:134`: says to load `download_url` into `<runefoble-map-uploader>`. The element takes `previewUrl`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0013, ADR-0014.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Show the generated asset id in the forge element and expose it to the shell.
2. Finish the preview URL form named in TASK-0645.
3. Fix the feature path and the how-to.

## Frontdoor Blackbox Test Plan
- A Storybook story shows the id after a generation.
- `pnpm run e2e:typecheck` passes with the fixed feature.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `.audit/work/0645.md` (Gaps)
