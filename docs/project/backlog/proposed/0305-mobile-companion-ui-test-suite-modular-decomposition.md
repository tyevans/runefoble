---
id: '0305'
title: Mobile Companion UI Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0134
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0005
- ADR-0013
governing_prds:
- PRD-0019
governing_stories:
- US-0059
target_release: 0.8.0
---

# TASK-0305: Mobile Companion UI Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_mobile_companion_ui.py` (297 lines, 59.4% of limit) into modular test submodules under `tests/test_blackbox_mobile_companion_ui/` (`conftest.py`, `test_manifest_and_styles.py`, `test_haptic_gateway.py`, `test_webrtc_signaling.py`), keeping each file strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_mobile_companion_ui.py` consolidates mobile companion microfrontend manifest checks, CSS token styling verifications, WebSocket haptic ping message delivery, and WebRTC peer room SDP exchange in a single 297-line test suite. As absentee voting controls and push notifications are extended, this test suite will breach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Architecture & Voice Audio**: WebRTC and haptic event verification.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Standardized modular test package layout.
- **ADR-0005: Kubernetes-First Infrastructure & Ingress Routing**: Gateway WebSocket route testing.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Microfrontend asset and shadow DOM verification.

## Scope of Work
1. **Shared Fixtures Submodule (`tests/test_blackbox_mobile_companion_ui/conftest.py`)**:
   - Extract mock Redis bus, SpiceDB mock client, and mobile companion manager lifecycle fixtures (< 60 lines).
2. **Manifest & Styles Tests (`tests/test_blackbox_mobile_companion_ui/test_manifest_and_styles.py`)**:
   - Extract microfrontend manifest schema verification and shadow DOM style bundle validation (< 75 lines).
3. **Haptic Gateway Tests (`tests/test_blackbox_mobile_companion_ui/test_haptic_gateway.py`)**:
   - Extract WebSocket secret ping triggers, vibration pattern payload verifications, and auth validation (< 85 lines).
4. **WebRTC Signaling Tests (`tests/test_blackbox_mobile_companion_ui/test_webrtc_signaling.py`)**:
   - Extract voice room SDP offer/answer exchange, low-bandwidth Opus mode assertions, and peer teardown (< 85 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_mobile_companion_ui/` to verify test suite passes.

## Definition of Done
- `tests/test_blackbox_mobile_companion_ui.py` replaced by `tests/test_blackbox_mobile_companion_ui/` package.
- All extracted submodules strictly < 100 lines each per Hard Invariant 6.
- 100% test coverage preserved with identical test pass assertions.
- Pytest and ruff checks pass cleanly.
