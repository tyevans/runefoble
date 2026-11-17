---
id: '0566'
title: Minigame Table State Through the Tavern Game Aggregate
status: Refined
created: 2026-11-17
dependencies:
- TASK-0560
- TASK-0565
governing_adrs:
- ADR-0011
- ADR-0007
governing_prds:
- PRD-0024
governing_stories:
- US-0047
- US-0074
target_release: 0.9.0
severity: high
source_audits:
- w1-game-session.md
---

# TASK-0566: Minigame Table State Through the Tavern Game Aggregate

## Status
Refined

## Summary
Minigame bets, dart throws, Liar's Dice bids, and roulette spins live in a process-memory dict in the WebSocket manager. A separate `TavernGameAggregate` already exists for the same games. This task routes every minigame action through that aggregate, keeps only socket connections in memory, and deletes the table dict.

## Problem Statement
- `services/game_session/src/game_session/minigame_tables/ws_manager.py:29-31` keeps `self.tables: dict[str, MinigameTableState]`.
- `routers/minigames_ws.py:46` calls `get_or_create_table` on the in-memory manager. `place_bet`, `throw_dart`, `submit_bid`, `spin_roulette`, and `roll_craps` run at lines 62-107.
- `routers/tavern.py:105-117` writes the same games through `TavernGameAggregate`. Two state paths exist (w1-game-session F4).
- AGENTS.md Hard Invariant 2 forbids domain state outside aggregates.

## Documentation & Architecture Review
- `docs/how-to/run-tavern-minigames-and-merchant-haggling.md` describes the games. Check it before coding.
- `proposed/0309-game-session-minigames-modular-decomposition.md` covers decomposition only. Coordinate file moves with it. Do not duplicate its work.

## Product & User Story References
- [`us-0047-tavern-minigames-and-merchant-haggling.md`](../../user_stories/accepted/us-0047-tavern-minigames-and-merchant-haggling.md)
- [`us-0074-interactive-mobile-tavern-and-casino-minigames.md`](../../user_stories/accepted/us-0074-interactive-mobile-tavern-and-casino-minigames.md)

## Detailed Specification & Implementation Plan
1. Add the commands `place_bet`, `throw_dart`, `submit_bid`, `spin_roulette`, `roll_craps` to `TavernGameAggregate` as `@handles`-backed commands that create events.
2. The WebSocket handler loads the aggregate by table id from `tavern_repo`, applies the command, saves, and broadcasts the stored event.
3. `MinigameTableManager` keeps only socket connection sets. Delete `tables` and `get_or_create_table` state.
4. A table id that does not exist is created by an explicit `OpenTable` command, not implicitly by a socket connect.

## Frontdoor Blackbox Test Plan
- **Fail before, pass after:** open a table through the public route, place a bet over the WebSocket, restart the app (fresh process against the same store), then `GET /api/v1/tavern/tables/{id}`. Before: bet lost. After: bet present.
- **Fail before, pass after:** a dart throw over the WebSocket appears as a `DartThrown` event on the tavern stream.
- Use only public routes and sockets.

## Definition of Done
1. `MinigameTableManager` holds no game state. Grep shows no `tables` dict.
2. Restart test above passes. Stream test passes.
3. `uv run pytest` and `make health-check` pass. Files under 500 lines.
4. `CHANGELOG.md` entry. How-to unchanged unless its statements become false.
