---
id: '0655'
title: Gherkin and Playwright Coverage for Lobby, Launch, Text and Voice Token Moves, and Character Sheet
status: Refined
created: 2026-11-17
dependencies:
- TASK-0652
- TASK-0649
- TASK-0950
- TASK-0945
- TASK-0947
governing_adrs:
- ADR-0014
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0005
- PRD-0006
- PRD-0023
- prd-0025-voice-first-release-one
governing_stories:
- US-0001
- US-0014
- US-0043
- US-0065
- US-0069
target_release: 1.0.0
---

# TASK-0655: Gherkin and Playwright Coverage for Lobby, Launch, Text and Voice Token Moves, and Character Sheet

## Status
Refined. Updated 2026-11-19 for Release One (PRD-0025). Evidence from `.audit/research/r1-core-journeys.md`, section 3.

## Summary
The second half of the core journey plan: a DM prepares a session in the lobby and launches it, a player moves a token by a typed command and by voice, and a player edits a character sheet. Write the Gherkin scenarios first. Then add steps that use only public frontdoors.

The typed move depends on TASK-0945, which adds the command bar. The voice move depends on TASK-0947, which adds the fake-microphone e2e path after the voice tasks TASK-0942 to TASK-0946. Until those land, the voice scenario does not pass. It is tagged `@requires-stt` and runs only when the speech-to-text gate is set (TASK-0947).

Launch does not depend on readiness. TASK-0952 sets this rule (PRD-0025: a missing player never cancels game night).

## Problem Statement
- Lobby and launch are covered by a partial feature (`session_lobby_and_vtt.feature`, US-0065). The launch step is a UI click in `e2e/steps/battlemap_setup_steps.ts:50-59`, not in `vtt_setup_steps.ts`. `vtt_steps.ts` is 166 lines.
- The drag uses real mouse input in `e2e/steps/battlemap_setup_steps.ts:61-90`. The check that follows (`vtt_steps.ts:139-152`) confirms only that a token exists in the target cell. It does not read the board state.
- No typed command input exists. `frontend/src/views/session-view.ts` renders the board, the character card, the feed and the voice panel only. TASK-0945 adds the input.
- The voice panel emits only DOM events. `services/voice_agent/ui/src/runefoble-voice-controls.ts:153-162` dispatches `voice-toggle`. The `voice-state` event (`:64-72`) has no listener. No UI code calls the transcribe or intent routes.
- "A player who is not ready cannot launch" is not a product rule. The launch control depends on the DM role only (`services/game_session/ui/src/lobby/runefoble-session-lobby.ts:54-56`). TASK-0952 sets the launch rule.
- The character sheet scenario (`character_sheet.feature`) uses fallback ids. TASK-0650 is complete and removed them (`e2e/support/guards.ts:5-7`).
- The encumbrance step (`character_sheet_steps.ts:298-305`) checks only that a label is visible. It must check a value.

## Documentation & Architecture Review
- `docs/how-to/interact-with-tactile-board-and-ghost-previews.md` describes the board move flow. Use its terms.
- `docs/how-to/interact-with-character-sheet-and-inventory.md` describes the sheet. Use its terms.
- `docs/how-to/coordinate-game-session-lobby-and-readiness.md`: update with the launch rule from TASK-0952.
- ADR-0013: the board and sheet are composed components. The App Shell mounts them; the test does not reach inside their shadow roots except to read visible labels.
- ADR-0022 (grammar-first voice routing) governs the voice scenario through TASK-0943 to TASK-0947.

## Product & User Story References
- [`us-0001-player-commands-board-via-voice.md`](../../user_stories/accepted/us-0001-player-commands-board-via-voice.md)
- [`us-0014-realtime-board-websocket-sync.md`](../../user_stories/accepted/us-0014-realtime-board-websocket-sync.md)
- [`us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md`](../../user_stories/accepted/us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md)
- [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)
- [`us-0069-character-sheet-inspector-and-active-session-binding.md`](../../user_stories/accepted/us-0069-character-sheet-inspector-and-active-session-binding.md)
- PRD-0025, "What good looks like", steps 2 to 4.

## Detailed Specification & Implementation Plan
1. Write `e2e/features/core_session_and_sheet.feature` first. Scenarios (story tag in brackets):
   - `@US-0065` A DM opens the lobby of a prepared session, sees the count of seats that are not ready, and launches the session. The launch does not wait for readiness (TASK-0952). The launch control is visible, and the URL changes to the session.
   - `@US-0065` A player who is not the DM sees no launch control. (The same rule is covered by `session_lobby_roles.feature:25-30`. Keep it here so that the journey is complete.)
   - `@US-0014` `@US-0043` A player types "move Valeros two squares north" in the command bar (TASK-0945). The board token moves two cells. The chronicle shows the move. The step reads `GET /api/v1/boards/{id}` and checks the cell.
   - `@US-0014` A DM drags a token to a cell. The cell label updates in a second browser context through the board socket.
   - `@US-0069` A player edits a character's HP through the sheet and sees the new value after reload.
   - `@US-0069` A player adds an item to inventory. The encumbrance value changes to the expected number.
   - `@US-0001` `@requires-stt` A player holds Push to Talk and says "move Valeros two squares north". The fake microphone and the real speech-to-text engine are used (TASK-0947). The board moves. The step prints the release-to-ghost time.
2. Text move: use the command bar from TASK-0945. This task does not add it.
3. Steps in `e2e/steps/session_steps.ts` and `e2e/steps/sheet_steps.ts`. Setup uses `frontdoor_api.ts`, except for the invite join, which uses the UI (TASK-0950).
4. Keep each file under 500 lines.

## Frontdoor Blackbox Test Plan
- Six scenarios run in chromium, firefox, and webkit. The voice scenario runs only when the speech-to-text gate of TASK-0947 is set.
- Before the work, the typed move and encumbrance scenarios do not exist. The lobby scenarios are partial today. After the work, all scenarios pass.
- Each token move asserts the board state from the public board route (`GET /api/v1/boards/{id}`) as well as the visible cell.

## Definition of Done
1. `e2e/features/core_session_and_sheet.feature` exists with the scenarios above, each tagged with its story id.
2. The six scenarios that do not need speech-to-text pass in all three browsers.
3. The voice scenario is tagged `@requires-stt`. It runs under the gate that TASK-0947 defines. It is not tagged `@blocked-voice`.
4. No step dispatches a synthetic event or writes private state (TASK-0649 grep check).
5. The encumbrance step checks a numeric value.
6. Each file is under 500 lines.
7. The launch rule in `docs/how-to/coordinate-game-session-lobby-and-readiness.md` matches the scenario.

## Audit Provenance

- Severity: high
- Source audits: `w2-e2e-bdd.md`, `w2-voice-agent.md`; `.audit/research/r1-core-journeys.md` (section 3, 0655 table)
