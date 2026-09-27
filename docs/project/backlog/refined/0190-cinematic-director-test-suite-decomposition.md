---
id: '0190'
title: Cinematic Director Blackbox Test Suite Modular Decomposition
status: Refined
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
Refined

## Summary
Decompose `tests/test_blackbox_cinematic_director.py` (342 lines, 68.4% of limit) into focused modular test sub-suites under `tests/test_blackbox_cinematic_director/` (`conftest.py`, `test_obs_overlay_routes.py`, `test_cinematic_camera.py`, `test_spectator_websocket.py`), keeping all test modules strictly < 150 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_cinematic_director.py` contains 342 lines verifying OBS party vitals HTML canvas rendering, alpha transparency styling, cubic-bezier camera interpolation, real-time spectator WebSockets, sanitization invariants, and microfrontend manifest registrations in a single file. As Milestone 9 introduces spectator mobile directives and multi-camera views, this monolithic test suite risks exceeding 400 lines unless decomposed into modular test suites.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular test package structure.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain separation between OBS presentation, cinematic camera tracking, and spectator WebSockets.
- **ADR-0010: Real-Time WebSocket Board Synchronization**: Proper spectator stream event verification.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Microfrontend manifest and component isolation.

## Detailed Specification & Implementation Plan
1. **Shared Fixtures (`tests/test_blackbox_cinematic_director/conftest.py`)**:
   - Extract test client, mock sessions, camera coordinates, and party state fixtures (< 60 lines).
2. **OBS Overlay Routes (`tests/test_blackbox_cinematic_director/test_obs_overlay_routes.py`)**:
   - Transparent OBS party vitals HTML canvas rendering, CSS alpha-channel verification, layout customization, and JSON sanitization (< 120 lines).
3. **Cinematic Camera Math (`tests/test_blackbox_cinematic_director/test_cinematic_camera.py`)**:
   - Cubic-bezier math evaluation, ease curve interpolation, TurnStarted centering, and TokenMoved destination tracking (< 110 lines).
4. **Spectator WebSockets & Manifest (`tests/test_blackbox_cinematic_director/test_spectator_websocket.py`)**:
   - WebSocket connection handshake, sanitized initial state delivery, turn/movement camera updates, and microfrontend manifest advertisement (< 120 lines).
5. **Verification**:
   - Remove root test module `tests/test_blackbox_cinematic_director.py` and run `uv run pytest tests/test_blackbox_cinematic_director/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Test refactoring isolated entirely to the cinematic director test package.
- **Negotiable (N)**: Test division follows clear sub-domains: OBS overlay rendering, camera math, WebSocket streaming.
- **Valuable (V)**: Safeguards against Hard Invariant 6 (500 lines) and speeds up test execution and maintenance.
- **Estimable (E)**: Deterministic extraction of test cases into discrete test modules with shared `conftest.py`.
- **Small (S)**: Bounded strictly to `tests/test_blackbox_cinematic_director/`; all modules < 150 lines.
- **Testable (T)**: Frontdoor verification through pytest test suite execution against public endpoints and WebSockets.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `test_blackbox_cinematic_director.py` replaced by decomposed submodules under `tests/test_blackbox_cinematic_director/`.
   - All extracted test files strictly < 150 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest tests/test_blackbox_cinematic_director/`.
3. **Quality Gates**:
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
