---
id: '0071'
title: WebSocket Zanzibar Authorization and Mutator Test Suite Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0008, TASK-0010, TASK-0016]
governing_adrs: [ADR-0001, ADR-0003, ADR-0005]
target_release: 0.2.0
---

# TASK-0071: WebSocket Zanzibar Authorization and Mutator Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_websocket_zanzibar_auth.py` (330 lines, 66.0% of limit) into two specialized test suites (`tests/test_websocket_zanzibar_connect_auth.py` and `tests/test_websocket_zanzibar_mutators.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as live SpiceDB gRPC clients (TASK-0035) and spectator interactivity (TASK-0051) expand permission boundaries.

## Problem Statement
`tests/test_websocket_zanzibar_auth.py` currently spans 330 lines and covers two distinct authorization checkpoints:
1. WebSocket connection handshake authentication and campaign viewer/reader authorization (`/ws/campaigns/{id}?user_id={user_id}`), including rejection of unauthorized subjects with 4003 codes and `PERMISSION_DENIED` frames.
2. In-session action mutators, verifying fine-grained Zanzibar object-level permissions on token movement, DM-only monster spawning and scene changes, character sheet mutations, and dynamic relation revocations.

As production SpiceDB gRPC connections (TASK-0035) and live spectator interaction channels (TASK-0051) add additional permission checks, this test file will soon exceed 500 lines unless modularized.

## Proposed Decomposition
1. **Connection Handshake Auth Suite (`tests/test_websocket_zanzibar_connect_auth.py`)**:
   - Connection validation for campaign readers and viewers.
   - Rejection and disconnection (code 4003) for unauthorized subjects.
   - Dynamic permission revocation disconnecting active sessions (< 160 lines).
2. **Game Action Mutator Auth Suite (`tests/test_websocket_zanzibar_mutators.py`)**:
   - Token movement permission checks (player ownership vs spectator denial).
   - DM-only action guards (monster spawning, scene alterations).
   - Redis Streams mutation event publication and foreign character sheet edit denials (< 190 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors test suite organization without changing production gateway WebSocket or authorization middleware logic.
- **Negotiable (N)**: Split boundaries between connection lifecycle and action mutators can be refined.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and speeds up targeted auth test execution.
- **Estimable (E)**: Clean separation of handshake authorization tests from payload mutator verification.
- **Small (S)**: Scope strictly isolated to `tests/test_websocket_zanzibar_auth.py`; all resulting files < 200 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_websocket_zanzibar_*.py`.

## Acceptance Criteria
1. `tests/test_websocket_zanzibar_auth.py` decomposed into focused test suites strictly under 200 lines each.
2. 100% test pass rate across all existing connection and mutator authorization tests.
3. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
4. Maintains blackbox frontdoor interactions via public WebSocket endpoints and standard domain events.
