---
id: '0040'
title: Modular APIRouter Decomposition for The Watcher & Game Session Microservices
status: Complete
created: 2026-09-25
dependencies:
- TASK-0002
- TASK-0013
- TASK-0022
governing_adrs:
- ADR-0007
- ADR-0009
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/25
---
# TASK-0040: Modular APIRouter Decomposition for The Watcher & Game Session Microservices

## Status
Refined

## Summary
Decompose monolithic `main.py` entrypoints in `services/the_watcher` (471 lines) and `services/game_session` (467 lines) into modular FastAPI `APIRouter` modules before they breach Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
Health scans identify `services/the_watcher/src/the_watcher/main.py` (471 lines, 94.2% of limit) and `services/game_session/src/game_session/main.py` (467 lines, 93.4% of limit) as high-risk refactoring candidates. Both services have accumulated numerous domain capabilities:
- In `the_watcher`: Speech intent parsing, autonomous scene generation, encounter spawning, NPC turns, stand-in decisions, absence penalties, and absentee chronicle recaps are all bundled into a single file.
- In `game_session`: Session CRUD, participant join/leave presence, combat initiative tracking, turn progression, and absentee stand-in autopilot trigger endpoints are in a single file.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal module layout of routers without modifying public HTTP endpoint paths, payload schemas, or domain event schemas.
- **Negotiable (N)**: Router package layout and helper module names can be structured to best reflect bounded contexts.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (<500 lines) and improves developer velocity and maintainability in core services.
- **Estimable (E)**: Standard FastAPI `APIRouter` extraction patterns.
- **Small (S)**: Scope strictly targets `the_watcher` and `game_session` routers; all resulting files < 200 lines.
- **Testable (T)**: Existing blackbox integration test suites (`test_game_session.py`, `test_the_watcher.py`, `test_stand_in_engine.py`, etc.) execute through public HTTP endpoints and verify zero regression.

## Governing Architecture & ADRs
- **ADR-0007**: Domain-Driven Design Architecture (bounded context microservices).
- **ADR-0009**: The Watcher Autonomous DM Architecture.

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

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Router Decomposition**:
   - Sub-routers created and mounted on FastAPI instances in both `the_watcher` and `game_session`.
2. **Public API Contract Preservation**:
   - Zero changes to public HTTP routes, status codes, OpenAPI schemas, request bodies, or responses.
3. **File Length Compliance**:
   - All touched source files strictly < 250 lines (well below the 500-line limit).
4. **Frontdoor Blackbox Verification**:
   - 100% test pass rate across existing unit and blackbox integration test suites via public HTTP frontdoor.
