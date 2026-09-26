---
id: '0075'
title: Spectator View Stream Clean Overlay and Broadcast Test Suite Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0014]
governing_adrs: [ADR-0003, ADR-0004, ADR-0013]
target_release: 0.2.0
---

# TASK-0075: Spectator View Stream Clean Overlay and Broadcast Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_spectator_view.py` (331 lines, 66.2% of limit) into two specialized test modules (`tests/test_spectator_events_and_schema.py` and `tests/test_spectator_stream_overlay.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as live audience interactivity (TASK-0051) and OBS stream overlays (TASK-0056) expand broadcast capabilities.

## Problem Statement
`tests/test_spectator_view.py` currently spans 331 lines and validates multiple facets of the spectator broadcast pipeline:
1. `SpectatorSessionConnected` CloudEvents 1.0 schema compliance and EventRegistry registration.
2. State sanitization rules stripping hidden tokens, monster stat blocks, secret DM lore, and private chronicle entries to prevent stream spoiling.
3. FastMCP / ASGI REST endpoint handling (`/api/v1/spectator/sessions/{id}`) and live WebSocket streaming broadcast (`/ws/spectator/{id}`).

As upcoming Milestone 4 broadcast features (Audience Studio interactivity in TASK-0051 and Cinematic Director OBS overlays in TASK-0056) add viewer voting, cheer reactions, and dynamic camera choreography tests, this single test suite will quickly breach the 500-line ceiling unless modularized.

## Proposed Decomposition
1. **Event Registration & Sanitization Unit Suite (`tests/test_spectator_events_and_schema.py`)**:
   - `SpectatorSessionConnected` event registry and CloudEvents 1.0 specification tests.
   - Comprehensive state sanitization logic tests (hidden tokens, private notes, secret encounters, monster stat blocks) (< 160 lines).
2. **Spectator Stream & Endpoint Blackbox Suite (`tests/test_spectator_stream_overlay.py`)**:
   - HTTP REST `/api/v1/spectator/sessions/{id}` retrieval of sanitized stream state.
   - Live WebSocket `/ws/spectator/{id}` connect handshake, initial state frame delivery, and real-time sanitized broadcast updates (< 180 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Modularizes test suite organization without changing gateway spectator routes, sanitization helpers, or WebSockets.
- **Negotiable (N)**: Split boundaries between event/sanitizer unit tests and ASGI WebSocket blackbox tests can be adapted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and speeds up focused spectator broadcast test cycles.
- **Estimable (E)**: Clean separation of pure state sanitization logic from ASGI client transport tests.
- **Small (S)**: Scope strictly isolated to `tests/test_spectator_view.py`; all resulting files < 190 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_spectator_*.py`.

## Acceptance Criteria
1. `tests/test_spectator_view.py` decomposed into focused test suites strictly under 200 lines each.
2. 100% test pass rate across all existing spectator schema, sanitization, and stream broadcast tests.
3. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
4. Maintains blackbox frontdoor interactions via public HTTP routes and WebSockets.
