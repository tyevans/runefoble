---
id: '0711'
title: Every Service Serves Its Vendored UI Manifest
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0013
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0711: Every Service Serves Its Vendored UI Manifest

## Status
Complete

## Summary
Seven services return a hardcoded component dict from `/ui/manifest`. The dicts differ from the vendored `ui/manifest.json` files. One service has no vendored manifest. All services must load the vendored file with `load_ui_manifest`.

## Problem Statement
- Hardcoded dicts: `services/game_session/src/game_session/main.py:97`, `services/campaign_analytics/src/campaign_analytics/main.py:142`, `services/asset_forge/src/asset_forge/main.py:73`, `services/board_state/src/board_state/routers/boards.py:27`, `services/voice_agent/src/voice_agent/main.py:113`, `services/rules_compendium/src/rules_compendium/main.py:77`, `services/campaign_lore/src/campaign_lore/main.py:120`.
- The loader exists: `libs/runefoble_platform/src/runefoble_platform/ui_manifest.py:20` (`load_ui_manifest`). Soundscape uses it (`services/soundscape/src/soundscape/main.py:29`).
- Drift: `game_session` hardcodes four components missing from its vendored file (`runefoble-bulletin-board`, `runefoble-dm-negotiation-drawer`, `runefoble-merchant-haggler`, `runefoble-minigame-darts`). `campaign_analytics` hardcodes `runefoble-campaign-telemetry`, also missing.
- `services/asset_forge/ui/` has no `manifest.json`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0013, ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. For each of the seven services, load `ui/manifest.json` at start with `load_ui_manifest` and return it. Delete the dicts.
2. Add the missing components to the vendored manifests of `game_session` and `campaign_analytics`. Create `services/asset_forge/ui/manifest.json` from the real components in `services/asset_forge/ui/src`.
3. Check that each service image copies `ui/manifest.json` (Dockerfiles and Helm). Fix any gap.
4. Update `docs/reference/microfrontend-architecture.md`.

## Frontdoor Blackbox Test Plan
- `GET /ui/manifest` on each of the seven services equals the parsed vendored file.
- A service with a missing manifest does not start.
- Every component in a manifest has a matching Custom Element tag in the service `ui/src`.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r1/libs.md`
