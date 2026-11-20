---
id: '0972'
title: The Session Binds the Caller's Own Character, Never Another Player's
status: Refined
created: 2026-11-19
dependencies:
- '0951'
governing_adrs:
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds:
- PRD-0025
governing_stories:
- us-0065-game-session-lobby-readiness-and-launch
target_bc: frontend
target_release: 1.0.0
---

# TASK-0972: The Session Binds the Caller's Own Character, Never Another Player's

## Status

Refined

## Summary

On Kind (2026-11-19), Sarah rolled a d20 and every chronicle showed "Valeros the Bold 1d20 = 17". Marcus, who has no character, saw a roll button. The App Shell binds the session view to `pickActiveCharacter` (`frontend/src/app/active-character.ts:12-14`): the first character of the campaign, else the first character at all. `fetchCharacters` returns every campaign character that the caller can see, so a player gets whichever character comes first. The roller name, the character card, the stance drawer and the stand-in state all read this binding.

## Problem Statement

- `frontend/src/app/active-character.ts:13`: `characters.find((c) => c.campaignId === campaignId) ?? characters[0] ?? null`. The `characters[0]` fallback is a substitute value (ADR-0015).
- `services/character_sheet/ui/src/roster/types.ts:30` has `ownerId?`, but no frontend mapper fills it. The server roster view sends `owner_id` (`services/character_sheet/src/character_sheet/roster.py:41`).
- `frontend/src/runefoble-app.ts:188-192` (`resolveActiveCharacter`) and `frontend/src/views/session-view.ts:65`.
- Evidence: e2e `session_dice_roll.feature` (speaker name, no-character roller) and `session_end_and_recap.feature` (recap dice line under the roller's name).

## Detailed Specification & Implementation Plan

1. Map `owner_id` to `ownerId` in the character mapper. A character without `owner_id` from the server is a malformed reply where the view needs ownership.
2. The active character is the caller's own character in the campaign (`ownerId === currentUserId`). When the session has seats, prefer the seat of the caller. With no own character, the result is null and the view shows its empty state (no roll button, no character card). No fallback to another character.
3. The DM's "switch character" control (`frontend/src/app/character-actions.ts`) keeps working for characters the DM may control; check it against SpiceDB capabilities the shell already reads, not a role string.
4. Lit rule: bind object/array inputs through `guard` (docs/how-to/develop-lit-components-in-storybook.md section 11).

## Frontdoor Blackbox Test Plan

- Node and DOM tests: with two players' characters in the roster, each caller binds only their own; a caller with none binds null; the roller gets the caller's character name.
- Orchestrator on Kind: `session_dice_roll.feature` and `session_end_and_recap.feature` pass.

## Definition of Done

- Tests pass. CHANGELOG `Fixed` line in the report.

## Audit Provenance

- Severity: high (one player's actions show under another player's character).
- Source audits: Kind e2e run 2026-11-19 (`/tmp/e2e_r1_1.log`).
