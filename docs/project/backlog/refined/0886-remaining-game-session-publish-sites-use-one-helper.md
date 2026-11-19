---
id: '0886'
title: Remaining Game Session Publish Sites Use One Helper
status: Refined
created: 2026-11-19
dependencies:
- '0858'
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0886: Remaining Game Session Publish Sites Use One Helper

## Status

Refined. Follow-up of TASK-0858.

## Summary

TASK-0858 added `publish_aggregate_events` and used it in 12 game_session files. Three groups of publish code remain. Two of them use best effort on routes that change state, which breaks the documented publish failure policy. This task moves them to the shared helper.

## Problem Statement

- `services/game_session/src/game_session/settlement/workers/loaders.py:26` and `services/game_session/src/game_session/settlement/haven/loaders.py:32`: local `save_and_publish` helpers call `publish_best_effort`. About 9 callers in `settlement/workers/*` and `settlement/haven/routes_*` change state. `docs/reference/redis-streams-event-bus.md` ("Publish Failure Policy") says routes that change state use `publish_or_fail` and return 503.
- `services/game_session/src/game_session/routers/caravan_contracts/auth.py:54`: `_publish` is a local copy of the publish loop. `lifecycle.py` and `board.py` import it.
- `docs/reference/redis-streams-event-bus.md` ("Aggregate Event Publication") says routers do not publish aggregate events. Only the session repository path works that way. Many game_session routers publish after the save.

## Documentation & Architecture Review

- ADR-0011: state changes are saved, then events are published.
- `docs/reference/redis-streams-event-bus.md`: publish failure policy and helper table.

## Product & User Story References

None. This is an internal consistency task. The visible change is HTTP 503 (not 200) when the stream is unreachable on haven and worker routes.

## Detailed Specification & Implementation Plan

1. Remove both `save_and_publish` copies in the settlement loaders. Callers save, then call `publish_aggregate_events`. Keep the save order and stream constants.
2. Remove `_publish` in `caravan_contracts/auth.py`. Callers in `lifecycle.py` and `board.py` call `publish_aggregate_events`.
3. Correct the "Aggregate Event Publication" section: state that the session repository publishes through `SessionEventPublisher`, and that other game_session aggregates are saved and then published with `publish_aggregate_events`.
4. No compatibility alias for the removed helpers.

## Frontdoor Blackbox Test Plan

- Charter a haven through the public route. Make the Redis test double unreachable. Call one haven upgrade route and one worker route. Assert 503 and assert the saved state through the public read route.
- Post a caravan contract with an unreachable stream. Assert 503.

## Definition of Done

- No local publish loop or `save_and_publish` copy remains in game_session.
- The tests above pass. Targeted settlement and caravan suites pass.
- The reference doc is correct. CHANGELOG records the 200-to-503 change on haven and worker routes.

## Audit Provenance

- Severity: medium
- Source audits: .audit/work/0858.md
