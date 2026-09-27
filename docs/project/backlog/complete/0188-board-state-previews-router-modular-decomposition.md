---
id: 0188
title: Board State Previews Router Modular Decomposition
status: Complete
created: 2026-09-27
dependencies:
- TASK-0084
- TASK-0085
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0010
governing_prds:
- PRD-0013
governing_stories:
- US-0043
target_release: 0.7.0
pr_url: https://github.com/tyevans/runefoble/pull/248
---
# TASK-0188: Board State Previews Router Modular Decomposition

## Status
Refined

## Summary
Decompose `services/board_state/src/board_state/routers/previews.py` (345 lines, 69.0% of limit) by separating REST route preview calculations from the live WebSocket ghost preview connection hub into `previews_http.py` and `previews_ws.py`, keeping each module strictly < 150 lines per Hard Invariant 6 and ADR-0010.

## Problem Statement
`services/board_state/src/board_state/routers/previews.py` has grown to 345 lines because it combines HTTP POST endpoints for kinematic route previews and the interactive WebSocket route (`/ws/boards/{session_id}`) handling ghost preview proposals, movement confirmations, and cancellation events. Combining HTTP route handlers and real-time WebSocket connection state in one file makes maintenance harder and risks breaching file length limits as Milestone 9 physics and AoE snapping features evolve.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular router structure for `services/board_state/`.
- **ADR-0007: Domain-Driven Design Architecture**: Clear separation of HTTP calculation services and WebSocket protocol handlers.
- **ADR-0010: Real-Time WebSocket Board Synchronization**: Proper connection pooling and event broadcast segregation.

## Detailed Specification & Implementation Plan
1. **REST Previews Router (`services/board_state/src/board_state/routers/previews_http.py`)**:
   - Isolate `preview_token_move` and coordinate calculation endpoints (< 100 lines).
2. **WebSocket Hub Router (`services/board_state/src/board_state/routers/previews_ws.py`)**:
   - Isolate `/ws/boards/{session_id}` handler, message parsing, ghost proposals, and confirmation events (< 140 lines).
3. **Router Aggregator Facade (`services/board_state/src/board_state/routers/previews.py`)**:
   - Maintain backward compatibility by re-exporting the combined APIRouter (< 50 lines).
4. **Verification**:
   - Run `uv run pytest services/board_state/ tests/test_blackbox_board*.py` and verify all tests pass without regression.

## INVEST Criteria Evaluation
- **Independent (I)**: Router decomposition confined strictly to `services/board_state/src/board_state/routers/`.
- **Negotiable (N)**: HTTP vs WebSocket segregation provides clean architectural separation.
- **Valuable (V)**: Safeguards against Hard Invariant 6 (500 lines) and isolates WebSocket lifecycle concerns.
- **Estimable (E)**: Standard FastAPI APIRouter modularization pattern.
- **Small (S)**: Bounded strictly to `board_state/routers/`; all modules < 150 lines.
- **Testable (T)**: Frontdoor verification through pytest execution against public REST endpoints and WebSocket channels.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `services/board_state/src/board_state/routers/previews.py` reduced to strictly < 60 lines.
   - Extracted submodules strictly < 150 lines each.
2. **Frontdoor Test Verification**:
   - `uv run pytest services/board_state/ tests/test_blackbox_board*.py` passes cleanly.
3. **Quality Gates**:
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
