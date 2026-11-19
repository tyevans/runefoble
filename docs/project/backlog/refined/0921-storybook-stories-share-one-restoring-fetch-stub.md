---
id: '0921'
title: Storybook Stories Share One Fetch Stub That Restores the Original Fetch
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0013
governing_prds: []
governing_stories:
- US-0004
target_bc: platform
target_release: 0.9.0
---
# TASK-0921: Storybook Stories Share One Fetch Stub That Restores the Original Fetch

## Status
Refined

## Summary
Five story fetch stubs live in four packages. Three of them replace the global `fetch` and never put it back, so one story's stub stays active in the next story. One shared helper with a restore function removes the copies and the leak.

## Problem Statement
- `libs/runefoble_ui/src/story-fetch.ts:7` (`installTokenCheckingFetch`) and `:34` (`installAssetUploadFetch`): set `window.fetch` and return no restore.
- `services/asset_forge/ui/src/forge-story-fetch.ts:19-21` (`withMockFetch`): sets `globalThis.fetch` and returns no restore.
- `services/board_state/ui/src/runefoble-dm-trap-controls.stories.ts:114-127` (`stubFetchForStory`): own copy, with restore.
- `services/rules_compendium/ui/src/runefoble-rules-compendium.stories.ts:218-226` (`stubHomebrewFetch`): own copy, with restore.
- `services/game_session/ui/src/runefoble-caravan-board.stories.ts:209-226`: inline save and restore.

## Documentation & Architecture Review
- ADR-0004: stories run with zero console errors. ADR-0013: shared UI code lives in `@runefoble/ui-core`.
- `docs/how-to/develop-lit-components-in-storybook.md`: add the helper and its use.
- TASK-0765 (refined) adds stories for voice, board and shell elements. It uses this helper if this task lands first.
- DoR 9: delete `forge-story-fetch.ts` and update its importers. No re-export.

## Product & User Story References
- US-0004 (developer tests a component in Storybook).

## Detailed Specification & Implementation Plan
1. In `libs/runefoble_ui/src/story-fetch.ts`, add `installStoryFetch(routes: StoryRoute[]): { requests: RecordedRequest[]; restore: () => void }`. A route has a method, a URL match, a status and a JSON body (or a function that builds it). An unmatched request throws, as `withMockFetch` does now. Export it from the package index.
2. Rewrite `installTokenCheckingFetch` and `installAssetUploadFetch` as route builders for `installStoryFetch`, or delete them and update their callers.
3. Move the forge, board trap, rules compendium and caravan stories to the helper. Each story restores fetch in its cleanup (Storybook `beforeEach` return value or the loader cleanup).
4. Delete `services/asset_forge/ui/src/forge-story-fetch.ts` and the three local copies.

## Frontdoor Blackbox Test Plan
- Unit test in `libs/runefoble_ui/test/`: the helper records requests, throws on an unmatched request, and `restore()` puts back the original `fetch`.
- Storybook build and the zero console error check (ADR-0004) pass for the four packages.
- Playwright BDD for the print forge and the caravan board (`tests/test_blackbox_print_forge.py`, `tests/test_blackbox_caravan_board_ui.py`) pass.

## Definition of Done
- One fetch stub implementation in the repository. No story leaves a stub installed.
- Docs updated. `pnpm run build`, `make build` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `ui-tests.md` (F2)
