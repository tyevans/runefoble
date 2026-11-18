---
id: '0658'
title: Tutorial 02 Describes Only Results the Running Platform Produces
status: Complete
created: 2026-11-17
dependencies:
- TASK-0657
governing_adrs:
- ADR-0002
- ADR-0007
governing_prds:
- PRD-0001
- PRD-0002
governing_stories:
- US-0001
- US-0002
target_release: 0.9.0
---

# TASK-0658: Tutorial 02 Describes Only Results the Running Platform Produces

## Status
Complete

## Summary
Tutorial 02 is not executable as written. Steps 2 to 4 show canned output, fixture data, or wiring the code does not have. Rewrite it so that every expected result is what the platform returns today. Where a feature is not yet live, the step says so, names the blocking task, and does not show a sample result. Update the steps again when the blockers land.

## Problem Statement
- Step 3 (lines 30-31): the expected narration "Valeros stepped forward 2 squares." and "The Watcher observes your advance into the crypt." is returned for any transcript by `gateway/api/src/gateway_api/routers/tabletop.py:183-193` (removed) (`POST /api/v1/watcher/speak-and-act`). This is canned output.
- Step 3: no evidenced path from Push to Talk to The Watcher. `services/voice_agent/ui/src/runefoble-voice-controls.ts:64-72` and `:140-150` emit only DOM events. No UI calls `/api/v1/voice/transcribe` or `/api/v1/watcher/intent*`.
- Step 2 (token count): the tutorial lists four tokens that match `FALLBACK_BOARD_TOKENS` (`app-data-service.fixtures.ts:146-151`). The live gateway board has two tokens, Valeros and Kyra (`gateway/api/src/gateway_api/campaign_store/sessions.py` (removed)). The live feed comes from a fixture until TASK-0641 lands.
- Step 4 (automatic stand-in): the Watcher's automatic evaluation is not persisted or triggered. `services/game_session/src/game_session/routers/autopilot.py:122` saves, but its trigger depends on `is_stand_in_active`, which is never set (`w1-character-sheet` F4). `WATCHER_SERVICE_URL` is not set by Helm.
- Lines 19 and 25: penalty labels "🍺 Drunk (Missed Session)" and "✨ Foolishness". Code labels are "Drunk (Session Miss)" and "Foolishness (Session Miss)" (`services/character_sheet/ui/src/templates/conditions.template.ts:66`).

## Documentation & Architecture Review
- `docs/tutorials/` is Diataxis learning-oriented. Keep the learner's path, but state each limit.
- `docs/explanation/the-watcher-autonomous-dm.md` describes the intended design. Link to it for the target state, and keep the tutorial to what runs.
- Blocking tasks to name in the tutorial: TASK-0600 to TASK-0602 (voice), TASK-0641 (chronicle feed), TASK-0640 (no fixtures), and the stand-in activation work in the character-sheet theme.

## Product & User Story References
- [`us-0001-player-commands-board-via-voice.md`](../../user_stories/accepted/us-0001-player-commands-board-via-voice.md)
- [`us-0002-absent-player-mimicked-by-ai-with-penalties.md`](../../user_stories/accepted/us-0002-absent-player-mimicked-by-ai-with-penalties.md)

## Detailed Specification & Implementation Plan
1. Rewrite each step with: the action, the expected observable result from the running platform, and a status line (`Available`, or `Not yet available: TASK-xxxx`).
2. Step 3: describe the text route only if the App Shell exposes it. Otherwise mark voice as not available and point to the blocker.
3. Step 2: show the live board after seeding through the UI. The number of tokens must come from the running board. Use the real penalty labels from the UI.
4. Step 4: mark the automatic stand-in as not yet available with the blocker. Do not describe the Watcher's response.
5. Remove every sample transcript and sample narration string that the code returns as fixed output.
6. Add a "Current limits" section listing each blocker with its task id.
7. Keep the tutorial under 200 lines.

## Frontdoor Blackbox Test Plan
- A reviewer runs each step on a local stack using only the UI and the documented public routes, and records the observed result in the task file.
- Acceptance check: every quoted string in the tutorial appears in a live response or a live UI state. A grep script (`scripts/check_tutorial_strings.sh` (removed)) compares quoted strings against `gateway/api/src` and `frontend/src` literals and fails on a match to a canned response.
- Before the rewrite the check fails on "Valeros stepped forward 2 squares." After the rewrite it passes.

## Definition of Done
1. Tutorial 02 has no sample output that the code returns as fixed output.
2. Each step is labelled Available or Not yet available with a task id.
3. The string check script passes and is documented in `docs/reference/cli-interfaces.md`.
4. The tutorial is re-verified after TASK-0640 and TASK-0641 land, and the status lines are updated in the same change if they landed.
5. Files stay under 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w3-docs-integrity.md`
