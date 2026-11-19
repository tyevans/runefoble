---
id: '0920'
title: Services Share One UI Manifest Router
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0013
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: platform
target_release: 0.9.0
---
# TASK-0920: Services Share One UI Manifest Router

## Status
Complete

## Summary
Ten services copy the same `GET /ui/manifest` handler and the same module-level `UI_MANIFEST = load_ui_manifest(...)` line. The loader already lives in `runefoble_platform`. One router factory removes the copies.

## Problem Statement
- `libs/runefoble_platform/src/runefoble_platform/ui_manifest.py:20`: `load_ui_manifest(path)` is shared. No router is shared.
- Copies: `services/asset_forge/src/asset_forge/main.py:31-32`, `:91-94`; `services/campaign_analytics/src/campaign_analytics/main.py:48-50`, `:93-96`; `services/campaign_lore/src/campaign_lore/main.py:41-44`, `:132-135`; `services/character_sheet/src/character_sheet/main.py:35-36`, `:84-87`; `services/game_session/src/game_session/main.py:48-49`, `:112-115`; `services/rules_compendium/src/rules_compendium/main.py:26-27`, `:88-91`; `services/soundscape/src/soundscape/main.py:29-30`, `:96-99`; `services/voice_agent/src/voice_agent/main.py:63-64`, `:125-128`; `services/board_state/src/board_state/routers/boards.py:31-32`, `:41-44`; `services/the_watcher/src/the_watcher/routers/ui_manifest.py:19-22` (removed).

## Documentation & Architecture Review
- ADR-0013 and `docs/reference/microfrontend-architecture.md` (`/ui/manifest` discovery). `docs/how-to/authoring-service-microfrontends.md` and `docs/how-to/create-a-new-service-bc.md` show the handler: update them.
- ADR-0015 problem 4: a missing manifest still stops the service at start-up.
- TASK-0859 and TASK-0916 edit some of the same `main.py` files. Rebase on whichever lands first.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `ui_manifest_router(manifest_path: Path, *, summary: str) -> APIRouter` to `ui_manifest.py`. It loads the manifest once when called, so a missing file fails at app build.
2. In each service, include the router and delete the local constant and handler. Delete `the_watcher/routers/ui_manifest.py`.
3. Keep the OpenAPI operation for `/ui/manifest` in each service spec.

## Frontdoor Blackbox Test Plan
- `GET /ui/manifest` on each of the ten services returns the same JSON as before (existing manifest tests).
- Building one service app with a missing manifest path raises at build time.

## Definition of Done
- `grep -rn "def get_ui_manifest" services/*/src` returns nothing.
- Docs updated. `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `services-backend.md` (finding 3)
