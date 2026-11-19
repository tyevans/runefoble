---
id: '0923'
title: The Session Socket Gets Dice, Turn and Whisper Frames From Domain Events
status: Refined
created: 2026-11-19
dependencies:
- '0910'
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: gateway
target_release: 0.9.0
---

# TASK-0923: The Session Socket Gets Dice, Turn and Whisper Frames From Domain Events

## Status

Refined. Follow-up of TASK-0910 (`.audit/work/0910.md`).

## Summary

Before TASK-0910, live dice rolls, turn changes and DM whispers reached other viewers only because a client sent those frames itself, and any player could forge them. TASK-0910 stopped clients from sending server kinds. No server produces them, so the dice, turn and whisper listeners in the App Shell now get no live messages. The gateway must produce these frames from the published domain events.

## Problem Statement

- `gateway/api/src/gateway_api/session_frames.py`: after TASK-0910, `dice_rolled`, `turn_advanced`, `dm_whisper`, `token_moved` and `session_started` are server kinds. Only `session_started` has a producer (the start route).
- `libs/runefoble_events/src/runefoble_events/session.py:51`: `runefoble.events.session.turn_advanced` is published on the session stream.
- Dice rolls and DM whispers: find the events that game_session and the_watcher publish (dice roll route; Watcher whisper route) and their streams (`docs/reference/events-catalog-gameplay.md`, `events-catalog-characters-watcher.md`).

## Documentation & Architecture Review

- `docs/how-to/run-supervised-redis-stream-consumers.md`: supervised consumers in a service lifespan, status on `/healthz`.
- `docs/reference/redis-streams-event-bus.md`: streams and consumer groups.
- `docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md`: a whisper is private to the DM.

## Product & User Story References

- Live table sync (`docs/explanation/realtime-voice-and-board-sync.md`).

## Detailed Specification & Implementation Plan

1. The gateway runs a supervised consumer on the session stream (and the Watcher stream for whispers). It maps each event to one frame and broadcasts it to the sockets of that session. It reports its status on `/healthz`.
2. `dm_whisper` goes only to sockets whose caller holds `session.control` (or the permission that the whisper how-to names). Never to players or spectators.
3. `token_moved`: if board_state already publishes a move event, map it too; otherwise record that the board socket owns live moves.
4. Idempotent on redelivery: a reclaimed message does not send a frame twice (source event id ledger, as in soundscape).
5. Update `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md`: remove the "no producer" note.

## Frontdoor Blackbox Test Plan

- Through public routes: a DM advances the turn; DM and player sockets each receive one `turn_advanced` frame. A dice roll through the public route gives one `dice_rolled` frame to each socket.
- A DM whisper reaches the DM socket and not the player or spectator socket.
- A redelivered event gives no second frame.
- Playwright on Kind (orchestrator): the lobby and VTT scenarios that show dice or turns.

## Definition of Done

- Tests above pass. Docs and CHANGELOG `Added` entry.

## Audit Provenance

- Severity: high
- Source audits: .audit/work/0910.md
