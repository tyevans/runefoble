---
id: '0655'
title: Gherkin and Playwright Coverage for Lobby, Launch, Text and Voice Token Moves, and Character Sheet
status: Refined
created: 2026-11-17
dependencies:
- TASK-0652
- TASK-0649
governing_adrs:
- ADR-0014
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0005
- PRD-0006
- PRD-0023
governing_stories:
- US-0001
- US-0014
- US-0043
- US-0065
- US-0069
target_release: 0.9.0
---

# TASK-0655: Gherkin and Playwright Coverage for Lobby, Launch, Text and Voice Token Moves, and Character Sheet

## Status
Refined

## Summary
The second half of the core journey plan: a DM prepares a session in the lobby and launches it, a player moves a token by text command and by voice, and a player edits a character sheet. Write the Gherkin scenarios first. Then add steps that use only public frontdoors. The voice scenario cannot pass until the voice path reaches The Watcher (`docs/tutorials/02-running-your-first-session.md` step 3 and `w1-gateway-api` F6 say it does not). It is therefore split into a text scenario that runs now and a voice scenario tagged `@blocked-voice`.

## Problem Statement
- Lobby and launch are covered by a partial feature (`session_lobby_and_vtt.feature`, US-0065). The launch step can fall back to a hash route (`vtt_steps.ts:189-196`, fixed in TASK-0649).
- Token moves are covered only by a drag with a synthetic event (`vtt_steps.ts:233-252`, fixed in TASK-0649). No text-command move exists in the UI.
- The voice path does not reach The Watcher. `services/voice_agent/ui/src/runefoble-voice-controls.ts:64-72` emits only DOM events. No UI calls `/api/v1/voice/transcribe` or `/api/v1/watcher/intent*` (`docs/tutorials/02` step 3 evidence, cross-referenced in `w3-docs-integrity.md` T7).
- The character sheet scenario (`character_sheet.feature`) uses fallback ids (TASK-0650 removes them). It does not cover a stand-in or a condition change.

## Documentation & Architecture Review
- `docs/how-to/interact-with-tactile-board-and-ghost-previews.md` describes the board move flow. Use its terms.
- `docs/how-to/run-campfire-rests-and-alchemical-crafting.md` is not part of this task.
- `docs/how-to/interact-with-character-sheet-and-inventory.md` describes the sheet. Use its terms.
- ADR-0013: the board and sheet are composed components. The App Shell mounts them; the test does not reach inside their shadow roots except to read visible labels.
- The voice scenario is blocked. Record the blocker in the feature file tag and in `docs/project/backlog/` when the voice tasks (TASK-0600 to TASK-0602) land.

## Product & User Story References
- [`us-0001-player-commands-board-via-voice.md`](../../user_stories/accepted/us-0001-player-commands-board-via-voice.md)
- [`us-0014-realtime-board-websocket-sync.md`](../../user_stories/accepted/us-0014-realtime-board-websocket-sync.md)
- [`us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md`](../../user_stories/accepted/us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md)
- [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)
- [`us-0069-character-sheet-inspector-and-active-session-binding.md`](../../user_stories/accepted/us-0069-character-sheet-inspector-and-active-session-binding.md)

## Detailed Specification & Implementation Plan
1. Write `e2e/features/core_session_and_sheet.feature` first. Scenarios (story tag in brackets):
   - `@US-0065` A DM opens the lobby of a prepared session, sees each player's readiness, and launches the session when all are ready. (Launch control visible, URL changes to the session.)
   - `@US-0065` A player who is not ready cannot launch; the launch control is disabled or absent for the player role.
   - `@US-0014` `@US-0043` A player types "move Valeros two squares north" in the command box; the board token moves two cells, and the chronicle shows the move from the public events route.
   - `@US-0014` A DM drags a token to a cell; the cell label updates for a second browser context (realtime sync through `/ws/session`).
   - `@US-0069` A player edits a character's HP through the sheet and sees the new value after reload.
   - `@US-0069` A player adds an item to inventory; the encumbrance indicator updates.
   - `@US-0001` `@blocked-voice` A player speaks a move command; the board moves within the budget in the design principles. Blocked until the voice path reaches The Watcher.
2. Text move: confirm the text command input exists in the UI first. If it does not, add the control in the owning UI package (`services/board_state/ui`) as part of this task, and document it in `docs/reference/`.
3. Steps in `e2e/steps/session_steps.ts` and `e2e/steps/sheet_steps.ts`. Setup uses `frontdoor_api.ts`.
4. Keep each file under 500 lines.

## Frontdoor Blackbox Test Plan
- Six scenarios run now in chromium, firefox, and webkit. The voice scenario is excluded by tag until unblocked.
- Before the work, the text move and sheet scenarios do not exist. The lobby scenarios are partial today. After the work, all six pass.
- Each token move asserts the board state from the public board route (`GET /api/v1/boards/{id}`) as well as the visible cell.

## Definition of Done
1. `e2e/features/core_session_and_sheet.feature` exists with the scenarios above, each tagged with its story id.
2. The six non-voice scenarios pass in all three browsers.
3. The voice scenario is tagged `@blocked-voice` and excluded from `make test-e2e`. Its unblock condition is written in the feature file.
4. No step dispatches a synthetic event or writes private state (TASK-0649 grep check).
5. Each file is under 500 lines.
6. The text command control, if added, appears in the component's Storybook story with zero console errors.

## Audit Provenance

- Severity: high
- Source audits: `w2-e2e-bdd.md`, `w2-voice-agent.md`
