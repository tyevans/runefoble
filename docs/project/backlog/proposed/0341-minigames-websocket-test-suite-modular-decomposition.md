---
id: '0341'
title: Minigames WebSocket Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0261
- TASK-0264
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0074
target_release: 0.8.0
---

# TASK-0341: Minigames WebSocket Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_minigames_websocket.py` (330 lines, 66.0% of limit) into modular test submodules under `tests/test_blackbox_minigames_websocket/` (`conftest.py`, `test_tavern_games.py`, `test_casino_games.py`), ensuring all test submodules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_minigames_websocket.py` tests both multiplayer tavern turn synchronization (darts and billiards, turn sequences, throw mechanics, trick shot gambits) and casino betting/payout mechanics (craps pass line, dice rolls, payouts, roulette wheel spins, odd/even bets) across long WebSocket connections within a single 330-line file. As spectator betting and live tournament matches are integrated, this file will breach the 500-line invariant limit unless modularized into focused test suites.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Real-time event propagation and stream broadcasting.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain boundaries.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 130 lines).

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_minigames_websocket/conftest.py`)**:
   - Extract test client setup, mock Redis event bus, SpiceDB mock, and WebSocket helper fixtures (< 60 lines).
2. **Tavern Minigames Tests (`tests/test_blackbox_minigames_websocket/test_tavern_games.py`)**:
   - Extract darts throwing, billiards cue angle/power physics, turn rotation, and game conclusion assertions (< 120 lines).
3. **Casino Minigames Tests (`tests/test_blackbox_minigames_websocket/test_casino_games.py`)**:
   - Extract craps betting rounds, roulette wheel spins, odds resolution, and wallet payout ledger checks (< 120 lines).
4. **Verification**:
   - Safely remove root `tests/test_blackbox_minigames_websocket.py` and ensure `uv run pytest tests/test_blackbox_minigames_websocket/` passes 100%.

## Definition of Done
- `tests/test_blackbox_minigames_websocket/` submodules strictly < 130 lines each per Hard Invariant 6.
- Root `tests/test_blackbox_minigames_websocket.py` safely removed.
- Passes all tests via `uv run pytest tests/test_blackbox_minigames_websocket/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
