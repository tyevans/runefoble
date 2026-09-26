# TASK-0003: Missing Player AI Stand-In Engine with Absence Penalties

## Description
Develop the missing player AI stand-in pipeline in `services/the_watcher`, `services/game_session`, and `services/character_sheet`. When a player is absent, their character is piloted by the AI engine with personality traits from their sheet and behavioral modifications driven by DM-inflicted penalties ("drunk", "foolishness", "cowardice", "greed").

## Governing Documents
- ADRs: ADR-0002, ADR-0007
- PRDs: PRD-0002
- User Stories: US-0002, US-0005

## Definition of Done
1. Characters marked as `is_stand_in_active = True` automatically take turns when prompted by `services/game_session`.
2. Penalties ("drunk", "foolishness", "cowardice", "greed") alter combat rolls (e.g. `1d20-2` for drunk rolls, distraction for foolishness), behavior, and vocal dialogue.
3. Stand-in actions emit `StandInActionDecided` and `AbsencePenaltyApplied` to `runefoble.events.watcher` and log to the session chronicle.
4. An absentee recap summary endpoint generates a humorous recap of actions for when the human player returns.

## Deliverables Completed
- [x] Enhanced `generate_stand_in_action` in `services/the_watcher/src/the_watcher/watcher_ai.py` supporting penalties ("drunk", "foolishness", "cowardice", "greed") and personality traits ("valiant", "impulsive", "scholarly") with dice modifications and dialogue flavoring.
- [x] Added `generate_stand_in_recap` in `services/the_watcher/src/the_watcher/watcher_ai.py` and endpoint `POST /api/v1/watcher/stand-in/recap` in `services/the_watcher/src/the_watcher/main.py` producing humorous session recaps and highlights for returning players.
- [x] Updated `services/the_watcher/src/the_watcher/main.py` to publish `StandInActionDecided` and `AbsencePenaltyApplied` events to Redis Streams (`runefoble.events.watcher`).
- [x] Enhanced `GameSessionAggregate` in `services/game_session/src/game_session/aggregate.py` to record stand-in actions with `record_stand_in_action` handling `StandInActionDecided` events.
- [x] Added `POST /api/v1/sessions/{session_id}/turns/auto-pilot` in `services/game_session/src/game_session/main.py` that verifies `is_stand_in_active`, invokes The Watcher engine, persists the stand-in action to session state, dispatches Redis events, and advances the turn.
- [x] Added comprehensive unit and integration tests in `tests/test_stand_in_engine.py` covering penalty mechanics, personality traits, Redis stream event publication, auto-pilot turn advancement, and humorous recap generation.
- [x] Verified full test suite passes (59/59) and Ruff lint and formatting checks are 100% clean.
