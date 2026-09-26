---
id: 0029
title: Frontdoor Blackbox Test Suite and Quality Gate Verification
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0026, TASK-0027]
governing_adrs: [ADR-0013]
target_release: 0.1.0
---

# TASK-0029: Frontdoor Blackbox Test Suite and Quality Gate Verification

## Status
Complete

## Summary
Constructed a dedicated blackbox test suite adhering to Hard Invariant 7 (`tests/test_microfrontends.py`) verifying public HTTP `/ui/manifest` discovery across all 5 service microservices, package structure integrity, App Shell composition, workspace declarations, and Storybook story discovery. Updated `tests/test_theming.py` to test theme token adoption on service microfrontends. Verified all continuous integration gates (`make test`, `make lint`, `make build`, and `pre-commit`).

## Key Changes
- `tests/test_microfrontends.py`:
  - `test_board_state_ui_manifest_frontdoor`: Verifies `board_state` manifest via `GET /ui/manifest`.
  - `test_character_sheet_ui_manifest_frontdoor`: Verifies `character_sheet` manifest via `GET /ui/manifest`.
  - `test_game_session_ui_manifest_frontdoor`: Verifies `game_session` manifest via `GET /ui/manifest`.
  - `test_the_watcher_ui_manifest_frontdoor`: Verifies `the_watcher` manifest via `GET /ui/manifest`.
  - `test_voice_agent_ui_manifest_frontdoor`: Verifies `voice_agent` manifest via `GET /ui/manifest`.
  - `test_service_ui_package_integrity`: Verifies `package.json`, `tsconfig.json`, and `@customElement` registrations.
  - `test_app_shell_microfrontend_composition`: Verifies `frontend/src/runefoble-app.ts` composition.
  - `test_monorepo_pnpm_workspace_declaration`: Verifies root `pnpm-workspace.yaml`.
  - `test_storybook_aggregates_service_stories`: Verifies Storybook discovery pattern.
- `tests/test_theming.py`:
  - Updated component paths to test theme token inheritance on the service microfrontends (`runefoble-board`, `runefoble-character-card`, `runefoble-watcher-feed`, `runefoble-voice-controls`).

## Verification
- `uv run pytest tests/test_microfrontends.py`: 9/9 passed.
- `make test`: 189/189 tests passed.
- `make lint`: Clean (0 errors).
- `make build`: Clean production build and Storybook build (0 errors).
