---
id: '0565'
title: Game Session Events Persisted Through Aggregates and Published to the Session Stream
status: Complete
created: 2026-11-17
dependencies:
- TASK-0560
governing_adrs:
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0001
- PRD-0005
governing_stories:
- US-0010
- US-0065
target_release: 0.9.0
severity: high
source_audits:
- w1-game-session.md
- w3-event-wiring.md
- w1-gates-python.md
---

# TASK-0565: Game Session Events Persisted Through Aggregates and Published to the Session Stream

## Status
Complete

## Summary
Game session state is event-sourced, but several session actions bypass the aggregate or never reach the stream. Session create, join, leave, and next-turn save events but do not publish them. Dice rolls and lobby readiness are not aggregate state at all. This task makes the repository publish every committed event, and moves dice rolls and lobby readiness into the session aggregate.

## Problem Statement
- `services/game_session/src/game_session/dependencies.py:41-44` builds repositories without `event_bus`, so `AggregateRepository.event_publisher` is `None` (w3-event-wiring F13).
- `services/game_session/src/game_session/routers/session.py:36-52` (create), `:80-94` (join), `:96-106` (leave), and `:173-182` (advance turn) call `repo.save` and never publish. `docs/reference/events-schema.md` says `TurnAdvanced`, `PlayerJoinedSession`, `PlayerLeftSession`, and `SessionEnded` are emitted (w1-game-session F5).
- `routers/session.py:185-219` evaluates a dice roll, builds `DiceRolled` directly, does not load a session, and suppresses the publish at `:205-207`. A roll for an unknown session succeeds (w1-game-session F6).
- `frontend/src/vtt-mesh-handlers.ts:78-85` keeps lobby readiness in client memory. `gateway/api/src/gateway_api/main.py:101-120` relays readiness frames to all clients without persistence. No readiness field exists in the aggregate (w1-game-session F9).

## Documentation & Architecture Review
- ADR-0011: state transitions are events saved through `AggregateRepository`.
- `docs/reference/redis-streams-event-bus.md` says projection workers run in production. That is false until TASK-0578 lands. Fix the statement with this task.
- Gateway relay of readiness is a gateway concern. Its auth belongs to the gateway theme. This task only makes the session aggregate the source of truth.

## Product & User Story References
- [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)
- [`prd-0005-realtime-websocket-board-sync.md`](../../product/accepted/prd-0005-realtime-websocket-board-sync.md)

## Detailed Specification & Implementation Plan
1. Pass the configured bus into the game-session repositories in `dependencies.py`. Add `publish_committed_events` to `AggregateRepository` usage so that every event returned by `save` is published to its stream. Choose the stream per event family in one mapping table in `game_session/events.py`.
2. Publish from the repository path for create, join, leave, and advance turn. Remove the per-route publish code they replace.
3. Add `DiceRollRecorded` on `GameSessionAggregate`. The route loads the session (404 when missing), calls the aggregate command with the roll result, saves, and lets the repository publish. Random generation stays in the command helper.
4. Add `ReadinessToggled` and `CharacterSelectedForLobby` to the aggregate. Expose `POST /api/v1/sessions/{id}/lobby/readiness`. The WebSocket carries the saved event only.
5. Update `docs/reference/events-schema.md` for the new events, and `docs/reference/redis-streams-event-bus.md` for the repository publish rule.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** subscribe to `runefoble.events.session` through the stream reader. Call `POST .../next-turn`. Before: no `TurnAdvanced`. After: one `TurnAdvanced` entry.
- **Fail before, pass after:** `POST /api/v1/sessions/{unknown}/dice/roll`. Before: 200. After: 404.
- **Fail before, pass after:** toggle readiness through the new route, then `GET /api/v1/sessions/{id}`. Before: no readiness field. After: readiness is returned.
- Setup uses only public routes. No direct state writes.

## Definition of Done
1. Every session route change is saved through an aggregate and published by the repository. No direct `publish` in routers for these events.
2. Three blackbox tests above pass. Events-schema reference updated.
3. `uv run pytest` and `make health-check` pass. Changed files under 500 lines.
4. `CHANGELOG.md` entry.
