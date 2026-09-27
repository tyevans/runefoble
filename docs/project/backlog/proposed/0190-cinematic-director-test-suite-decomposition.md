---
id: '0190'
title: Cinematic Director Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0056
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
target_release: 0.7.0
---

# TASK-0190: Cinematic Director Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_cinematic_director.py` (342 lines, 68.4% of limit) into focused modular test sub-suites under `tests/test_blackbox_cinematic_director/` (`test_obs_overlay_routes.py`, `test_cinematic_camera.py`, `test_spectator_websocket.py`, `test_spectator_microfrontend.py`), keeping all test modules strictly < 150 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_cinematic_director.py` contains 342 lines verifying OBS party vitals HTML canvas rendering, alpha transparency styling, cubic-bezier camera interpolation, real-time spectator WebSockets, sanitization invariants, and microfrontend manifest registrations. As Milestone 9 introduces spectator mobile directives and multi-camera views, this monolithic test suite risks exceeding 400 lines unless decomposed into modular test suites.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular test package structure.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain separation between OBS presentation, cinematic camera tracking, and spectator WebSockets.
- **ADR-0010: Real-Time WebSocket Board Synchronization**: Proper spectator stream event verification.
- **ADR-0013: Microfrontend Bounded Context Architecture**: Microfrontend manifest and component isolation.

## Scope of Work
1. **Modular Test Package (`tests/test_blackbox_cinematic_director/`)**:
   - `test_obs_overlay_routes.py`: Transparent OBS party vitals HTML canvas rendering, CSS alpha-channel verification, layout customization, and JSON sanitization (< 120 lines).
   - `test_cinematic_camera.py`: Cubic-bezier math evaluation, ease curve interpolation, TurnStarted centering, and TokenMoved destination tracking (< 110 lines).
   - `test_spectator_websocket.py`: WebSocket connection handshake, sanitized initial state delivery, turn/movement camera updates, and dice roll animations (< 120 lines).
   - `test_spectator_microfrontend.py`: Gateway manifest advertisement, custom element `<runefoble-spectator-overlay>` definition, and Storybook stories (< 60 lines).
2. **Backward Compatibility**:
   - Maintain `tests/test_blackbox_cinematic_director.py` as a lightweight re-exporting test shim (< 40 lines).
3. **Verification**:
   - Run `uv run pytest tests/test_blackbox_cinematic_director/` and verify all tests pass.

## Definition of Done
- `tests/test_blackbox_cinematic_director.py` decomposed into focused sub-suites under `tests/test_blackbox_cinematic_director/`.
- All test files strictly < 150 lines.
- All cinematic director blackbox tests pass via `uv run pytest`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
