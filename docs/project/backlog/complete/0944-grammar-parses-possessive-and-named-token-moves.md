---
id: '0944'
title: The Grammar Parses Possessive and Named-Token Moves
status: Complete
created: 2026-11-19
dependencies:
- '0943'
governing_adrs:
- ADR-0015
- ADR-0022
governing_prds:
- prd-0025-voice-first-release-one
governing_stories:
- us-0001-player-commands-board-via-voice
target_bc: the_watcher
target_release: 1.0.0
---

# TASK-0944: The Grammar Parses Possessive and Named-Token Moves

## Status

Complete

## Summary

The release phrase is "move my warrior to the chest". The grammar returns `narrative` for this phrase, so no board action is made. This task adds the possessive and named-token shapes to the grammar. The grammar records the target name. The destination is resolved by TASK-0942, from the board read.

## Problem Statement

- `services/the_watcher/src/the_watcher/grammars.py:43-46`: `MOVE_TO_TOKEN_PATTERN` needs "to", "towards" or a similar word right after the verb. "move my warrior to the chest" does not match.
- `services/the_watcher/src/the_watcher/movement_parser.py:59`: `parse_speech_intent(transcript, speaker_name)` takes no token list. The grammar cannot look up a token name. It must return the name only.
- `services/the_watcher/src/the_watcher/movement_parser.py:173`: a phrase with no match returns `narrative`.
- `services/the_watcher/src/the_watcher/movement_parser.py:96-103`: the flank pattern already returns `target_token` and `target` as a name. The new shape must use the same keys so that TASK-0942 reads them.
- `services/the_watcher/src/the_watcher/grammars.py:92-95`: `DICE_PATTERN` already matches "roll a d20". `movement_parser.py:166-168` returns `roll_dice`. This is a regression check only.
- `services/board_state` tokens have no class field. `services/the_watcher/src/the_watcher/board_client.py:11` lists the token fields: `token_id`, `name`, `token_type`, `x`, `y`, `hp`, `is_friendly`.

## Documentation & Architecture Review

- ADR-0022 (a): the grammar parses every transcript first. Its consequences list "The grammar must grow for the release phrases (possessives, token names, 'my <class>')".
- ADR-0015 Context item 4: the grammar does not guess a token. An unmatched name is an error, which TASK-0942 reports.
- `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`: update it if it lists the accepted phrases.

## Product & User Story References

- PRD-0025, "A spoken move goes nowhere", and "What good looks like" item 4.
- US-0001.

## Detailed Specification & Implementation Plan

1. Add one grammar shape for a possessive subject:
   - "move my <subject> to the <target>"
   - "move the <subject> to the <target>"
   - "<verb> my <subject> to <target>" for the verbs already in `MOVE_TO_TOKEN_PATTERN`
   The subject is one to three words. The target is a name of one to four words. A leading "the" is optional.
2. The grammar returns action `move` with parameters `{"action": "move_to_token", "subject": <subject>, "target_token": <target>, "target": <target>}`. The grammar does not read the board.
3. The moved token is always the speaker's own token, `req.token_id`. The subject is recorded in the parameters but is not matched. A board token has no class field, so the subject cannot be checked. A request with no `token_id` returns HTTP 422.
4. Two or more visible tokens that match the target name: the route returns HTTP 409, as TASK-0942 defines. Disambiguation by the player is out of scope for release one. State this in the docstring.
5. Keep the existing patterns and their order. The new shape goes after the coordinate and cardinal patterns and before the flank pattern.
6. Add a regression check that "roll a d20" still returns `roll_dice`.

## Frontdoor Blackbox Test Plan

Use the public gateway route `POST /api/v1/watcher/speak-and-act`, a live The Watcher, a live board_state, and the board WebSocket. Extend `tests/test_blackbox_gateway_speech_proxy.py` and `tests/test_blackbox_spoken_move_preview.py`. Set up the board only through public routes.

- Board with a warrior token and a chest token. Speak "move my warrior to the chest" as the warrior's player. The response is `move`. The board socket receives a staged `ghost_preview` on a free neighbour of the chest.
- Speak "move the warrior to the chest": the same result.
- Speak "move my warrior to the chest" with no `token_id` in the request: HTTP 422.
- Two tokens named "chest": HTTP 409. No frame arrives on the board socket.
- Speak "roll a d20": the response is `roll_dice`.
- Speak "move my warrior" with no target: the response is `narrative` (no board frame).

The grammar unit tests in `tests/test_speech_to_intent.py` may add cases. They do not replace the frontdoor tests.

## Definition of Done

- Every test in the plan passes, with `uv run pytest` on the named files.
- The existing grammar tests in `tests/test_speech_to_intent.py` still pass. The latency test at lines 146-172 still passes.
- `docs/how-to/interact-with-tactile-board-and-ghost-previews.md` lists the new shapes, if it lists the accepted phrases.
- A CHANGELOG `Added` entry under `[Unreleased]` names the new spoken move shapes.
- Every file the task touches stays under 500 lines.

## Audit Provenance

- Severity: high (PRD-0025 release blocker).
- Source audits: `.audit/research/r1-watcher-llm.md` ("Grammar: 'move my warrior to the chest' -> narrative"), `.audit/research/r1-voice-path.md` (section 7, slice S2).
