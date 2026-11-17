---
id: '0684'
title: One Shared Redis Streams Event Bus Factory With Fail-Fast Start-Up
status: Refined
created: 2026-11-17
dependencies:
- TASK-0672
governing_adrs:
- ADR-0003
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_release: 0.9.0
severity: high
source_audits:
- work/0672.md
---

# TASK-0684: One Shared Redis Streams Event Bus Factory With Fail-Fast Start-Up

## Status
Refined. Discovered during TASK-0672. Consolidation approved by the user at the round-10 pause (2026-11-17).

## Summary
Six services each define their own `get_event_bus()` that builds a `RedisStreamsEventBus`. `libs/runefoble_platform` also has a `get_event_bus()` that reads an undefined flag `use_redis_event_bus` and so always returns `InMemoryEventBus`; it has no callers. This task makes one shared factory in `libs/runefoble_platform`, connects it in each service's FastAPI lifespan, fails start-up when Redis is configured and unreachable, and deletes the copies and the dead in-memory path.

## Problem Statement
- Copies: `services/voice_agent/src/voice_agent/dependencies.py:28` and `main.py:72`, `services/voice_agent/src/voice_agent/stt.py:110`, `services/the_watcher/src/the_watcher/dependencies.py:154`, `services/game_session/src/game_session/dependencies.py:166`, `services/asset_forge/src/asset_forge/dependencies.py:55`, `services/board_state/src/board_state/dependencies.py:43`.
- `libs/runefoble_platform/src/runefoble_platform/event_sourcing.py:133-150`: dead factory with a silent in-memory fallback (DoR 9 and ADR-0015 conflict).
- TASK-0672 report: board_state has no lifespan and the bus connects lazily, so a Redis outage shows up only at the first publish.

## Documentation & Architecture Review
- `docs/reference/redis-streams-event-bus.md`: update the "how a service gets the bus" section.
- ADR-0015: deployed services fail fast when a configured backend is unreachable.

## Product & User Story References
None. Platform wiring with no user-facing change, except that events now reliably reach Redis.

## Detailed Specification & Implementation Plan
1. Add `create_event_bus(settings) -> RedisStreamsEventBus` and a lifespan helper `event_bus_lifespan(app)` in `libs/runefoble_platform`. The helper connects and pings Redis at start-up and raises a clear error if it fails. It stores the bus on `app.state`.
2. Add one FastAPI dependency `get_event_bus(request)` that reads `app.state`. Services import it from the lib.
3. Move each of the six services to the helper (add a lifespan where none exists). Delete the per-service factories and the platform `get_event_bus` / `InMemoryEventBus` export. Update all call sites and tests (tests use the existing Redis test double from the root conftest).
4. Check Helm: every service that publishes has `RUNEFOBLE_REDIS_URL`.

## Frontdoor Blackbox Test Plan
- Start a service app with the Redis URL pointing at a closed port: start-up fails with the clear error.
- With the Redis test double: a public route that emits an event puts one entry on the expected stream.
- `grep -rn "def get_event_bus" services/` returns nothing.

## Definition of Done
- One factory and one dependency in libs. No per-service copies. No in-memory bus in production code.
- Tests and helm-lint pass. Reference doc updated. CHANGELOG line given to the orchestrator.
