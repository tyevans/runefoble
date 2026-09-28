---
id: '0316'
title: Gateway Spectator Router and Stream Manager Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0014
- TASK-0056
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0013
governing_prds:
- PRD-0011
governing_stories:
- US-0014
- US-0040
target_release: 0.8.0
---

# TASK-0316: Gateway Spectator Router and Stream Manager Modular Decomposition

## Status
Proposed

## Summary
Decompose `gateway/api/src/gateway_api/spectator.py` (289 lines, 57.8% of limit) into modular submodules under `gateway/api/src/gateway_api/spectator/` (`models.py`, `sanitizer.py`, `router.py`), ensuring all modules remain strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`gateway/api/src/gateway_api/spectator.py` combines Pydantic data models (tokens, scenes, chronicles, state responses), sensitive state sanitization algorithms (stripping DM secrets, invisible tokens, monster HP/stats), and FastAPI endpoint route handlers in a single 289-line file. As audience chaos voting, OBS cinematic camera controls, and multi-camera views are integrated, this file will rapidly exceed 500 lines unless decoupled into single-responsibility modules.

## Governing Architecture & ADRs
- **ADR-0001: Fine-Grained Authorization with SpiceDB**: Spectator view isolation and non-disclosure of DM secrets.
- **ADR-0006: Redis Streams Event Bus**: Real-time spectator stream event fanout.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 120 lines).

## Scope of Work
1. **Spectator Models (`gateway/api/src/gateway_api/spectator/models.py`)**:
   - Pydantic schemas for `SpectatorToken`, `SpectatorSceneAtmosphere`, `SpectatorChronicleMessage`, and `SpectatorStateResponse` (< 80 lines).
2. **State Sanitizer (`gateway/api/src/gateway_api/spectator/sanitizer.py`)**:
   - Extraction of state filtering logic, DM secret scrubbing, and visibility redaction functions (< 100 lines).
3. **Route Handlers (`gateway/api/src/gateway_api/spectator/router.py`)**:
   - FastAPI APIRouter endpoints for stream overlays and state snapshots (< 110 lines).
4. **Facade Re-export (`gateway/api/src/gateway_api/spectator/__init__.py`)**:
   - Re-export models, router, and sanitization utilities maintaining full backward compatibility (< 30 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_spectator.py` to ensure zero regression.

## Definition of Done
- `gateway/api/src/gateway_api/spectator.py` migrated to `gateway/api/src/gateway_api/spectator/` package.
- All extracted submodules strictly < 120 lines each per Hard Invariant 6.
- Existing spectator tests and OBS overlay routes continue passing cleanly.
