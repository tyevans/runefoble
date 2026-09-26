---
id: '0040'
title: Modular APIRouter Decomposition for The Watcher & Game Session Microservices
status: Proposed
created: 2026-09-25
dependencies: [TASK-0002, TASK-0013, TASK-0022]
governing_adrs: [ADR-0007, ADR-0009]
target_release: 0.2.0
---

# TASK-0040: Modular APIRouter Decomposition for The Watcher & Game Session Microservices

## Status
Proposed

## Summary
Decompose monolithic `main.py` entrypoints in `services/the_watcher` (460 lines) and `services/game_session` (453 lines) into modular FastAPI `APIRouter` modules before they breach Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
Health scans identify `services/the_watcher/src/the_watcher/main.py` (460 lines, 92% of limit) and `services/game_session/src/game_session/main.py` (453 lines, 90.6% of limit) as high-risk refactoring candidates. Both services have accumulated numerous domain capabilities:
- In `the_watcher`: Speech intent parsing, autonomous scene generation, encounter spawning, NPC turns, stand-in decisions, absence penalties, and absentee chronicle recaps are all bundled into a single file.
- In `game_session`: Session CRUD, participant join/leave presence, combat initiative tracking, turn progression, and absentee stand-in autopilot trigger endpoints are in a single file.

## Proposed Decomposition
1. **The Watcher Microservice (`services/the_watcher/src/the_watcher/routers/`)**:
   - `routers/intent.py`: `/api/v1/watcher/intent` (Speech-to-intent parsing and event emission).
   - `routers/autonomous_dm.py`: `/api/v1/watcher/scenes`, `/encounter`, `/npc-turn`, `/autonomous-action`.
   - `routers/stand_in.py`: `/api/v1/watcher/stand-in` (AI stand-in actions and absence penalties).
   - `routers/chronicle.py`: `/api/v1/watcher/recap` (Session recap and chronicle generation).
   - Reduce `main.py` to a thin orchestration shell (< 80 lines) instantiating FastAPI and mounting routers.
2. **Game Session Microservice (`services/game_session/src/game_session/routers/`)**:
   - `routers/session.py`: `/api/v1/sessions` (Create, get, join, leave session).
   - `routers/combat.py`: `/api/v1/sessions/{id}/combat/*`, `/initiative`, `/next-turn`.
   - `routers/autopilot.py`: `/api/v1/sessions/{id}/autopilot`.
   - Reduce `main.py` to < 80 lines.

## Acceptance Criteria
1. Zero changes to public HTTP routes, status codes, request bodies, or responses.
2. All touched source files strictly < 250 lines (well below the 500-line limit).
3. 100% test pass rate across existing unit and blackbox integration test suites.
