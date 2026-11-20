---
id: '0945'
title: A Typed Command in the Session View Reaches the Board Preview
status: Refined
created: 2026-11-19
dependencies:
- '0942'
- '0944'
governing_adrs:
- ADR-0004
- ADR-0013
- ADR-0014
- ADR-0022
governing_prds:
- prd-0025-voice-first-release-one
governing_stories:
- us-0001-player-commands-board-via-voice
target_bc: the_watcher
target_release: 1.0.0
---

# TASK-0945: A Typed Command in the Session View Reaches the Board Preview

## Status

Refined. First user-facing slice of the voice loop. It proves the browser half of the board path without a microphone.

## Summary

The session view has no command input. A player can speak a move only through a path that no browser code uses yet. This task adds a typed command bar to the session view. The bar sends the text to the gateway speak-and-act route. The board shows the ghost preview. The player confirms it with the existing banner.

## Problem Statement

- `frontend/src/views/session-view.ts:59-61`: the session view mounts `<runefoble-voice-controls>` only. It mounts no command input.
- `services/*/ui/src` and `frontend/src`: no file calls `/api/v1/watcher/speak-and-act` or `/api/v1/watcher/transcribe-and-act`. A search returned no match.
- `gateway/api/src/gateway_api/routers/watcher_speech_proxy.py:23-39`: the gateway route exists. It forwards the raw JSON body to The Watcher. Its timeout is 5 s (`:19`).
- `services/board_state/ui/src/board-actions.ts:206-208` and `services/board_state/ui/src/runefoble-board.ts:191-197`: the board stages a `ghost_preview` and sends `confirm_move` on confirm. Both paths exist.
- `services/board_state/ui/src/templates/overlays.template.ts:102-110`: the ghost banner has confirm and cancel actions.
- `services/the_watcher/ui/src`: no command bar exists. The Watcher UI package holds `runefoble-dm-whisper-bar.ts` and the feed. The owning package for a speech command is `services/the_watcher/ui/`.
- `frontend/src/vtt-mesh-handlers.ts`: holds the board event handlers that post to the session socket. Use the same pattern for the command handler.

## Documentation & Architecture Review

- ADR-0004 and ADR-0013: a user-facing element is a Lit component in its owning package, built with Storybook, and listed in the package manifest. The App Shell mounts it and does not own its logic.
- ADR-0014: the scenario runs in Playwright through the UI only.
- ADR-0022 (c): a failed call shows the error. It does not hide the error.
- `docs/how-to/authoring-service-microfrontends.md` and `docs/how-to/develop-lit-components-in-storybook.md`.

## Product & User Story References

- PRD-0025, "No typed command exists", and "What good looks like" item 4 (he can also type the same command).
- US-0001.

## Detailed Specification & Implementation Plan

1. Create `<runefoble-command-bar>` in `services/the_watcher/ui/src/runefoble-command-bar.ts`, with a styles file and a stories file. Export it from `services/the_watcher/ui/src/index.ts` and list it in `services/the_watcher/ui/manifest.json` (`components` and `tags`).
2. The element takes these properties: `sessionId`, `campaignId`, `speakerId`, `speakerName`, `tokenId`, `fromX`, `fromY`, `gridCols`, `gridRows`. When `tokenId`, `fromX` or `fromY` is missing, the input is disabled and the element says "No character token is on the board."
3. Submit on the Send button or on Enter. The element emits `speak-command` with the body: `speaker_id`, `speaker_name`, `transcript`, `session_id`, `campaign_id`, `token_id`, `from_x`, `from_y`, `grid_cols`, `grid_rows`. It does not call the network.
4. The App Shell handler in `frontend/src/vtt-mesh-handlers.ts` posts the body to `POST /api/v1/watcher/speak-and-act` through the shared client (`docs/reference/ui-transport.md`). Set the bearer as the other board calls do.
5. A 2xx response: show the returned `watcher_reply` in the bar. The ghost arrives on the board socket. No other code path stages the ghost.
6. A non-2xx response: show the status and the detail text in the bar. Do not clear the typed text.
7. Mount the element in `frontend/src/views/session-view.ts` next to `<runefoble-voice-controls>` (`:59-61`). Pass the props from the app state: the board token of the active character, its cell, and the board size.
8. Do not change `frontend/src/views/session-view.ts:34` (the `confirm-ghost` forwarding). Note it as a known side path in the record of this task only.

## Frontdoor Blackbox Test Plan

- Playwright scenario `e2e/features/voice_typed_command.feature`. Steps use the UI only. Setup follows the Background of `e2e/features/session_lobby_and_vtt.feature` (campaign, seats, launch, battlemap set-up through the UI).
  - Valeros types "move 2 squares west" in the command bar and presses Enter.
  - The ghost banner appears on both screens. The banner names a cell two squares west of the token.
  - The token has not moved yet.
  - Valeros clicks Confirm. The token moves on both screens.
- Playwright scenario: Valeros types a transcript that the grammar does not parse, such as "dance nicely". The bar shows "Not understood." No ghost banner appears.
- Playwright scenario: the Watcher is down (run with the gateway route answered by the live Watcher stopped by the test harness). The bar shows the error. Use the existing fault helper in `e2e/support/service_faults.ts`.
- Storybook stories for the bar: idle, no token, sending, reply, error. Zero console errors.
- Unit test for the emitted body (Vitest in `services/the_watcher/ui/test/`).

## Definition of Done

- The Playwright scenarios pass on Kind (`make test-e2e`), with no backdoor setup.
- The Storybook stories build and show zero console errors.
- `services/the_watcher/ui/manifest.json` lists the element. `make check-ui-manifests` passes.
- `docs/reference/microfrontend-architecture.md` or the owning package reference lists the new element and its properties and event.
- A CHANGELOG `Added` entry under `[Unreleased]` says that players can type a command.
- Every file the task touches stays under 500 lines.

## Audit Provenance

- Severity: high (PRD-0025 release blocker).
- Source audits: `.audit/research/r1-voice-path.md` (section 7, slice S1; section 4 "What the first release needs instead").
