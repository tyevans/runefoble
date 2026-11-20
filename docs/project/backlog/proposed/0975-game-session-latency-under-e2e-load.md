---
id: '0975'
title: game_session Reads Stay Under the Gateway Budget When the Kind Host Is Loaded
status: Proposed
created: 2026-11-20
dependencies: []
governing_adrs:
- ADR-0015
- ADR-0005
governing_prds:
- PRD-0025
governing_stories: []
target_bc: game_session
target_release: 1.0.0
---

# TASK-0975: game_session Reads Stay Under the Gateway Budget When the Kind Host Is Loaded

## Status

Proposed

## Summary

During full Kind e2e runs, the gateway logs bursts of `Upstream game_session unavailable: ReadTimeout` (budget 5 s, `gateway/api/src/gateway_api/campaign_owner_call.py` `OWNER_TIMEOUT_S`). A burst often comes 1 s to 3 s after `POST /api/v1/sessions/{id}/start`. The App Shell then shows "Loading the battlemap..." or a stale roster, and an e2e scenario fails at random (0954 hidden-layer scenario, about 1 run in 4).

## Evidence (2026-11-20)

- Idle: `GET /readyz` from the gateway pod answers in 30 ms or less (60 calls).
- With `PYTHONASYNCIODEBUG=1` in the game-session pod, a stall shows about 20 back-to-back `_SelectorSocketTransport._read_ready()` callbacks of 0.3 s each, and no slow task.
- Postgres is not the source: one scenario reads 329 `events` rows. SpiceDB answers in under 60 ms during the stall, and its call rate drops because game_session stops calling it.
- The host load average was 18 to 20 on 16 cores during the runs. Zitadel was the top process.
- game-session used about 15% CPU with no traffic (asyncio debug was on at that time, so measure again without it).
- `py-spy` cannot attach (`ptrace_scope=1`, no sudo).

## Work

1. Take a stack sample during a stall. Options: give the pod `CAP_SYS_PTRACE` for a debug run, or add an opt-in in-process sampler.
2. Find which socket protocol parses for 0.3 s per read (Redis, SpiceDB gRPC thread contention for the GIL, or uvicorn).
3. Measure the idle CPU of game-session without debug mode, and explain it.
4. Decide if the e2e Kind stack needs CPU requests and limits, so Zitadel and the browsers cannot starve game_session.

## Definition of Done

- A full e2e run on Kind shows no game_session ReadTimeout in the gateway log.
- The root cause and the fix are recorded in this task.
