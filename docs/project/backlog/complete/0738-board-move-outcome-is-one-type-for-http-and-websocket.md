---
id: '0738'
title: Board Move Outcome Is One Typed Result for HTTP and WebSocket Moves
status: Complete
created: 2026-11-17
dependencies:
- TASK-0547
governing_adrs:
- ADR-0011
- ADR-0007
governing_prds:
- PRD-0005
governing_stories:
- US-0014
- US-0018
target_bc: board_state
target_release: 0.9.0
---
# TASK-0738: Board Move Outcome Is One Typed Result for HTTP and WebSocket Moves

## Status
Complete

## Summary
A move over the WebSocket drops the trap and pause fields, so a client that moves onto a trap gets no pause signal. `move_token` returns a tuple subclass and checks for a collaborator with `hasattr`.

## Problem Statement
- `services/board_state/src/board_state/routers/previews_ws.py:65`: `cost, hazard, dice = board.move_token(...)`. The `token_moved` message omits `trap_triggered` and `movement_paused`.
- `handlers/tokens.py:120`: `if breach is not None and hasattr(self, "spring_trap")`. `TrapsHandlerMixin` always provides it (`handlers/traps.py:62`), so the check hides a missing collaborator.
- `models/tokens.py:75-90`: `MoveResult(tuple)` holds three values in the tuple and two as attributes. `routers/tokens.py` unpacks it and reads the rest with `getattr`.
- `handlers/tokens.py:83` imports the trap evaluator inside `move_token`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0007.
- `docs/how-to/manage-secret-dm-traps-and-map-triggers.md`. TASK-0547 changes WebSocket auth on the same handler: run after it.

## Product & User Story References
- PRD-0005
- US-0014
- US-0018

## Detailed Specification & Implementation Plan
1. Replace `MoveResult` with a frozen dataclass `MoveOutcome` with all five fields.
2. Make the trap collaborator an explicit method on the aggregate. Remove `hasattr`. Move the evaluator import to module level.
3. HTTP and WebSocket paths send the same fields.

## Frontdoor Blackbox Test Plan
- Existing `tests/test_blackbox_traps/test_spatial_triggers_and_movement_pause.py` over HTTP.
- New: WebSocket `confirm_move` onto a trapped path. Assert `movement_paused` in the `token_moved` message.

## Definition of Done
- `grep -n hasattr` finds none in `handlers/tokens.py`.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `board-character-forge.md (F6)`
