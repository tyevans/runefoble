---
id: 0027
title: App Shell Decoupling, Voice Controls Microfrontend, and Storybook Aggregation
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0026]
governing_adrs: [ADR-0004, ADR-0012, ADR-0013]
target_release: 0.1.0
---

# TASK-0027: App Shell Decoupling, Voice Controls Microfrontend, and Storybook Aggregation

## Status
Complete

## Summary
Refactored `frontend/src/runefoble-app.ts` into a lightweight, decoupled **App Shell** that imports and orchestrates microfrontends from `@runefoble/*` packages. Extracted inline voice panel markup and styling into the `<runefoble-voice-controls>` microfrontend, reducing `runefoble-app.ts` file length from 453 to 396 lines (safely below the 400-line warning threshold). Maintained backwards-compatible forwarding re-exports in `frontend/src/components/`, and updated Storybook configuration to dynamically aggregate stories from all service bounded contexts.

## Key Changes
- `frontend/src/runefoble-app.ts`:
  - Replaced monolithic component imports with `@runefoble/*` workspace package imports.
  - Replaced inline voice panel with `<runefoble-voice-controls>`.
  - Focused strictly on shell layout, session metadata, theme switching, and WebSocket multiplexing.
- `frontend/src/components/`:
  - Implemented forwarding re-exports for `runefoble-board`, `runefoble-character-card`, `runefoble-absentee-recap`, `runefoble-watcher-feed`, `runefoble-autonomous-dm`, `runefoble-initiative-tracker`, `runefoble-dice-roller`, `runefoble-spectator-view`, and `runefoble-voice-controls`.
  - Retained `runefoble-theme-switcher.ts` as the App Shell design system component.
- `frontend/.storybook/main.ts`:
  - Added discovery pattern `'../../services/*/ui/src/**/*.stories.@(js|jsx|mjs|ts|tsx)'` to dynamically aggregate all domain stories.
- `frontend/tsconfig.json`:
  - Added path aliases for `@runefoble/*` packages and excluded external stories from production application builds.

## Verification
- `cd frontend && pnpm run build` succeeds (107ms).
- `cd frontend && pnpm exec storybook build --disable-telemetry --quiet` aggregates all stories with zero errors.
- `python3 scripts/health_check.py` verifies zero files exceed 500 lines.
