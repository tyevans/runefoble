---
id: '0942'
title: The Watcher's Spoken Move Resolves Its Destination
status: Complete
created: 2026-11-19
dependencies: []
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

# TASK-0942: The Watcher's Spoken Move Resolves Its Destination

## Status

Complete

## Summary

A spoken move stages a ghost preview. Today the preview has the same cell as the origin. The Watcher reads the wrong keys for the destination, and it defaults the origin to (0, 0). This task makes the Watcher read the destination that the intent carries. A named target token resolves to a free cell next to that token. A missing origin is a client error.

## Problem Statement

- `services/the_watcher/src/the_watcher/routers/intent/speech.py:73-74`: the origin defaults to 0 when `from_x` or `from_y` is absent.
- `services/the_watcher/src/the_watcher/routers/intent/speech.py:75-83`: the destination comes from `to_x`/`to_y` or from `dx`/`dy`. The default for `dx` and `dy` is 0.
- `services/inference_worker/src/inference_worker/models.py:52-53`: the worker returns `target_x` and `target_y`. The Watcher never reads these keys.
- `services/the_watcher/src/the_watcher/adapters/worker_engines.py:52`: the Watcher stores the whole worker action in `parameters`. The keys reach `_propose_move`, but `_propose_move` does not read them.
- `services/inference_worker/src/inference_worker/graphs/intent_graph.py:80-89`: a named target token gets the cell of that token. A move to that cell is a move to the same cell. The task needs a free cell next to the token.
- `services/the_watcher/src/the_watcher/movement_parser.py:72-73`: a coordinate move from the grammar sets `to_x`/`to_y` and `target_x`/`target_y`. The `dx`/`dy` path works for cardinal moves.
- `services/the_watcher/src/the_watcher/board_client.py:14-41`: `fetch_visible_tokens` returns `token_id`, `name`, `x`, `y` for each token on the board. This read is the source for the target lookup.
- `tests/test_blackbox_spoken_move_preview.py:118`: the one existing destination assertion covers only the cardinal path.

## Documentation & Architecture Review

- ADR-0015 Context item 4: a failure must show. A missing origin is a client error (422). The Watcher must not invent (0, 0).
- ADR-0022 (c): a failed step returns an error. It does not try another path.
- `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`: update it if it states the origin default or the destination rule.
- `docs/reference/ports-and-endpoints.md`: no change unless the route contract changes. The route path does not change.

## Product & User Story References

- PRD-0025, "A spoken move goes nowhere".
- US-0001 (player commands the board by voice).

## Detailed Specification & Implementation Plan

1. Read the origin from `req.from_x` and `req.from_y`. If either is missing, return HTTP 422 with a detail that names the missing field. Do this before any board call. Remove the default of 0.
2. Coordinate destination: if the intent parameters hold `to_x`/`to_y`, or `target_x`/`target_y`, use them as the destination. Read the keys in that order. A destination outside the grid (`req.grid_cols`, `req.grid_rows`) returns HTTP 422.
3. Named target token: if the intent names a token, match the name or `target_token_id` against the tokens from `fetch_visible_tokens`. The intent keys are `target_token`, `target_token_name`, `target_token_id` and `target`. Then choose the destination as follows:
   - Candidate cells are the eight neighbours of the target cell, inside the grid.
   - A candidate is free when no token on the board holds it.
   - Choose the free candidate nearest to the origin. Break ties by lower `y`, then lower `x`.
   - No token matches the name: HTTP 422.
   - Two or more tokens match the name: HTTP 409. No preview is staged.
   - No free candidate: HTTP 409. No preview is staged.
4. Distance move (`dx`/`dy`): keep the current behaviour. Compute the destination from the origin with `calculate_bounded_destination` (`services/the_watcher/src/the_watcher/spatial.py:50-52`).
5. Run the checks in steps 1 to 3 before `propose_move_preview` is called. An error stages no preview on any socket.
6. Keep the `SpeechIntentParsed` publish order as it is today.

## Frontdoor Blackbox Test Plan

Tests use the public gateway route `POST /api/v1/watcher/speak-and-act`, a live The Watcher, a live board_state, and the board WebSocket `/ws/boards/{session_id}`. Extend `tests/test_blackbox_spoken_move_preview.py`. Set up the board only through public routes. Do not mock a client.

- A named target token: the staged `ghost_preview` has the free neighbour of the target nearest the origin. The token does not move before `confirm_move`.
- A coordinate move with worker keys (`target_x`/`target_y`) and a coordinate move with grammar keys (`to_x`/`to_y`): each stages the given destination.
- No `from_x` in the request: HTTP 422. No frame arrives on the board socket.
- An unknown target name: HTTP 422. A duplicate target name: HTTP 409. A target with no free neighbour: HTTP 409.
- The worker case uses the real inference worker, reached on a live loopback URL. The test must not replace the worker with a stub.

## Definition of Done

- Every test in the plan passes. Tests run through `uv run pytest` for the named files.
- No code path reads a default origin of 0. Search `speech.py` for `else 0` to confirm.
- `docs/how-to/interact-with-tactile-board-and-ghost-previews.md` is updated if it states the old rule.
- A CHANGELOG `Fixed` entry under `[Unreleased]` says that a spoken move stages the requested destination.
- Every file the task touches stays under 500 lines.

## Audit Provenance

- Severity: high (PRD-0025 release blocker).
- Source audits: `.audit/research/r1-voice-path.md` (section 1, step 7-8; section 6), `.audit/research/r1-watcher-llm.md` ("A spoken move to a token gives a zero-length preview").
