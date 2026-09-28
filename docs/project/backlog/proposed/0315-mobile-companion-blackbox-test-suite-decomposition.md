---
id: '0315'
title: Mobile Companion Blackbox Test Suite Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0128
governing_adrs:
- ADR-0002
- ADR-0005
- ADR-0013
governing_prds:
- PRD-0004
- PRD-0019
governing_stories:
- US-0059
target_release: 0.8.0
---

# TASK-0315: Mobile Companion Blackbox Test Suite Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_mobile_companion.py` (293 lines, 58.6% of limit) into modular test sub-suites under `tests/test_blackbox_mobile_companion/` (`conftest.py`, `test_websocket_signaling.py`, `test_whisper_and_alerts.py`, `test_audio_profiles.py`), keeping each test file strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_mobile_companion.py` tests mobile companion WebSocket signaling, secret DM haptic whisper dispatch, turn alert notifications, and low-bandwidth Opus audio profile tier negotiation in a single 293-line file. As offline caching, remote voting, and absentee directives are expanded, this test suite will rapidly breach the 500-line ceiling unless partitioned.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Real-time companion event signaling.
- **ADR-0005: Zitadel Authentication & SpiceDB Authorization**: Mobile token authentication and Zanzibar permissions.
- **ADR-0013: Modular Decomposition**: All test modules kept strictly < 500 lines (submodules < 120 lines).

## Scope of Work
1. **Fixtures & Clean State (`tests/test_blackbox_mobile_companion/conftest.py`)**:
   - Clean SpiceDB mocks, Redis event bus, companion manager state, and test client (< 55 lines).
2. **WebSocket Signaling Suite (`tests/test_blackbox_mobile_companion/test_websocket_signaling.py`)**:
   - WebSocket connection, session registration, disconnect handling, and heartbeat (< 95 lines).
3. **Whispers & Turn Alerts Suite (`tests/test_blackbox_mobile_companion/test_whisper_and_alerts.py`)**:
   - Haptic vibration dispatch, secret DM whisper HTTP endpoints, and turn notification pings (< 110 lines).
4. **Adaptive Audio Profiles Suite (`tests/test_blackbox_mobile_companion/test_audio_profiles.py`)**:
   - Network profile tier adaptation, Opus bandwidth renegotiation, and profile events (< 95 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_mobile_companion/` to confirm all tests pass.

## Definition of Done
- `tests/test_blackbox_mobile_companion.py` decomposed into `tests/test_blackbox_mobile_companion/` package.
- All extracted test modules strictly < 120 lines each per Hard Invariant 6.
- 100% test pass rate preserved without regressions.
