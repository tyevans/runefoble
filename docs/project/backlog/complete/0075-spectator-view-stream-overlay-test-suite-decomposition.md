---
id: '0075'
title: Spectator View Stream Clean Overlay and Broadcast Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0014
- TASK-0051
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0004
- ADR-0007
- ADR-0009
- ADR-0013
target_release: 0.3.0
governing_prds:
- PRD-0011
governing_stories:
- US-0029
- US-0030
pr_url: https://github.com/tyevans/runefoble/pull/103
---
# TASK-0075: Spectator View Stream Clean Overlay and Broadcast Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_spectator_view.py` (330 lines, 66.0% of limit) into two specialized test modules (`tests/test_spectator_events_and_schema.py` and `tests/test_spectator_stream_overlay.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as live audience interactivity (TASK-0051) and OBS stream overlays (TASK-0056) expand broadcast capabilities.

## Problem Statement
`tests/test_spectator_view.py` currently spans 330 lines and validates multiple facets of the spectator broadcast pipeline:
1. `SpectatorSessionConnected` CloudEvents 1.0 schema compliance and EventRegistry registration.
2. State sanitization rules stripping hidden tokens, monster stat blocks, secret DM lore, and private chronicle entries to prevent stream spoiling.
3. FastMCP / ASGI REST endpoint handling (`/api/v1/spectator/sessions/{id}`) and live WebSocket streaming broadcast (`/ws/spectator/{id}`).

As upcoming Milestone 4 broadcast features (Audience Studio interactivity in TASK-0051 and Cinematic Director OBS overlays in TASK-0056) add viewer voting, cheer reactions, and dynamic camera choreography tests, this single test suite will breach the 500-line ceiling unless modularized.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Validating spectator redaction policies and safe public state views.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test module separation within root test runner.
- **ADR-0004: Lit Web Components and Storybook UI**: Overlay presentation validation.
- **ADR-0007: Real-Time Voice and Board Synchronization**: WebSocket stream broadcasting latency and frame delivery.
- **ADR-0009: Continuous Backlog Refinement and Technical Debt Management**: Preemptive test splitting.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Service component boundary testing.

## Product & User Story References
- **Product Requirement**: [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- **User Stories**:
  - [`us-0029-spectator-dynamic-cinematic-auto-camera.md`](../../user_stories/accepted/us-0029-spectator-dynamic-cinematic-auto-camera.md)
  - [`us-0030-obs-transparent-party-vitals-and-multi-track-audio.md`](../../user_stories/accepted/us-0030-obs-transparent-party-vitals-and-multi-track-audio.md)

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

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_spectator_view.py` decomposed into focused test suites strictly under 200 lines each.
2. 100% test pass rate across all existing spectator schema, sanitization, and stream broadcast tests.
3. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
4. Maintains blackbox frontdoor interactions via public HTTP routes and WebSockets.
5. Passes `uv run ruff check` and `uv run pytest tests/test_spectator_events_and_schema.py tests/test_spectator_stream_overlay.py`.
