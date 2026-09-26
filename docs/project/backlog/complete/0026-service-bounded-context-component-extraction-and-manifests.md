---
id: 0026
title: Service Bounded Context Component Extraction and HTTP Manifests
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0025]
governing_adrs: [ADR-0004, ADR-0013]
target_release: 0.1.0
---

# TASK-0026: Service Bounded Context Component Extraction and HTTP Manifests

## Status
Complete

## Summary
Extracted all domain presentation components from `frontend/src/components/` into their owning service bounded context directories (`services/<bc>/ui/src/`). Each bounded context now publishes its own npm package (`@runefoble/<bc>-ui`) with TypeScript configuration, package exports, and co-located interactive Storybook stories. Furthermore, added `GET /ui/manifest` discovery endpoints across all 5 service FastAPI entrypoints.

## Key Changes
- `services/board_state/ui/`:
  - Created package `@runefoble/board-state-ui` vendoring `<runefoble-board>` and stories.
  - Added `GET /ui/manifest` to `services/board_state/src/board_state/main.py`.
- `services/character_sheet/ui/`:
  - Created package `@runefoble/character-sheet-ui` vendoring `<runefoble-character-card>`, `<runefoble-absentee-recap>`, and stories.
  - Added `GET /ui/manifest` to `services/character_sheet/src/character_sheet/main.py`.
- `services/game_session/ui/`:
  - Created package `@runefoble/game-session-ui` vendoring `<runefoble-initiative-tracker>`, `<runefoble-dice-roller>`, `<runefoble-spectator-view>`, and client dice arithmetic utilities.
  - Added `GET /ui/manifest` to `services/game_session/src/game_session/main.py`.
- `services/the_watcher/ui/`:
  - Created package `@runefoble/the-watcher-ui` vendoring `<runefoble-watcher-feed>`, `<runefoble-autonomous-dm>`, and stories.
  - Added `GET /ui/manifest` to `services/the_watcher/src/the_watcher/main.py`.
- `services/voice_agent/ui/`:
  - Created package `@runefoble/voice-agent-ui` vendoring `<runefoble-voice-controls>` and stories.
  - Added `GET /ui/manifest` to `services/voice_agent/src/voice_agent/main.py`.

## Verification
- Verified each `/ui/manifest` endpoint via FastAPI TestClient in `tests/test_microfrontends.py`.
- All TypeScript packages compile with `tsc --noEmit`.
