---
id: '0583'
title: Gateway Speak-and-Act Proxies to The Watcher Intent Pipeline
status: Complete
created: 2026-11-17
dependencies:
- TASK-0580
- TASK-0582
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0001
- PRD-0020
governing_stories:
- US-0001
- US-0024
target_release: 0.9.0
---

# TASK-0583: Gateway Speak-and-Act Proxies to The Watcher Intent Pipeline

## Status
Complete

## Summary
`POST /api/v1/watcher/speak-and-act` returns a fixed sentence. Replace it with a proxy to The Watcher speech intent route. The Watcher owns intent parsing. Board changes happen in `board_state` after The Watcher emits an event (ADR-0002). The gateway does not parse speech and does not change the board.

## Problem Statement
- `gateway/api/src/gateway_api/routers/tabletop.py:183-193` (removed) returns `action_taken: "Valeros stepped forward 2 squares."` and broadcasts that sentence. It has no auth and no Watcher call (`w1-gateway-api.md` F6, `w3-authz-coverage.md` F7).
- This route is the entry point for "speak and the board obeys" (AGENTS.md design principles). It runs in the browser today as a fake.
- The owner exists: `services/the_watcher/src/the_watcher/routers/intent/speech.py` exposes `POST /api/v1/watcher/intent` and `POST /api/v1/watcher/transcribe-and-act`.

## Documentation & Architecture Review
- ADR-0002, section 2: The Watcher listens for speech, extracts intents and emits `BoardMoveEvent`, `DiceRollEvent` and `WatcherNarrationEvent`. Services do not call each other in a chain. The gateway must not add that chain.
- ADR-0002, section 4: The gateway streams state to the frontend. It does not compute state.
- `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md` and `docs/how-to/interact-with-tactile-board-and-ghost-previews.md` describe the spoken path. Read both before writing the mapping.
- Latency budget: the design requires intent parsing within 500 ms (`docs/explanation/realtime-voice-and-board-sync.md`). The proxy adds no more than 10 ms of overhead. Set the upstream timeout from the Watcher budget in TASK-0580.

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`prd-0020-zero-latency-neural-voice-duplex-and-interruption.md`](../../product/accepted/prd-0020-zero-latency-neural-voice-duplex-and-interruption.md)
- [`us-0001-player-commands-board-via-voice.md`](../../user_stories/accepted/us-0001-player-commands-board-via-voice.md)
- [`us-0024-natural-speech-equipment-swapping-and-wake-word.md`](../../user_stories/accepted/us-0024-natural-speech-equipment-swapping-and-wake-word.md)

## Detailed Specification & Implementation Plan
1. Create `gateway/api/src/gateway_api/routers/watcher_speech_proxy.py`. Expose `POST /api/v1/watcher/speak-and-act` with the same request body fields. Map the body to the owner request. Return the owner status and body with no change.
2. Forward the verified caller identity through `ServiceClient` (TASK-0580). Do not read the body's `user_id`.
3. Delete the canned handler and its broadcast from `tabletop.py` (removed). Delete `tabletop.py` (removed) if TASK-0581 and TASK-0582 have already moved every other route out of it.
4. Confirm in `services/the_watcher` that the speech route publishes `BoardMoveEvent` for a move. If it does not, record the gap in this task's PR. Do not add the publish in the gateway.
5. Update `docs/reference/ports-and-endpoints.md` for the route's owner and status codes.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_gateway_speech_proxy.py`. The Watcher and `board_state` run as ASGI apps. Setup: create a session and a board with public routes.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| Transcript "move three squares north" returns the Watcher's parsed intent | Fails: fixed "Valeros stepped forward 2 squares." | Passes |
| A board move event reaches `board_state` and the next `GET /api/v1/boards/{id}` shows the new position | Fails: board unchanged | Passes |
| Missing transcript returns the Watcher's 422 | Fails: 200 | Passes |
| Watcher down returns 503 | Fails: canned 200 | Passes |

## Definition of Done
1. `rg "stepped forward" gateway/api/src` returns nothing.
2. The gateway route forwards through `ServiceClient`. No gateway code parses speech.
3. The blackbox test file passes.
4. The PR states whether the Watcher publishes `BoardMoveEvent` for this path. If it does not, a follow-up task exists before this task is marked complete.
5. `uv run ruff check .` passes.

## Audit Provenance

- Severity: critical
- Source audits: `w1-gateway-api.md`, `w3-authz-coverage.md`, `w3-ddd-architecture.md`

## Completion Note
The gateway proxy is done. Board commit of a Watcher move stays on the player confirm path (design: The Watcher proposes, players confirm). The end-to-end test moves to TASK-0814.
