---
id: '0071'
title: WebSocket Zanzibar Authorization and Mutator Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0008
- TASK-0010
- TASK-0016
- TASK-0080
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0005
- ADR-0009
target_release: 0.3.0
governing_prds:
- PRD-0005
governing_stories:
- US-0014
pr_url: https://github.com/tyevans/runefoble/pull/102
---
# TASK-0071: WebSocket Zanzibar Authorization and Mutator Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_websocket_zanzibar_auth.py` (330 lines, 66.0% of limit) into two specialized test suites (`tests/test_websocket_zanzibar_connect_auth.py` and `tests/test_websocket_zanzibar_mutators.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as live SpiceDB gRPC clients (TASK-0035) and spectator interactivity (TASK-0051) expand permission boundaries.

## Problem Statement
`tests/test_websocket_zanzibar_auth.py` currently spans 330 lines and covers two distinct authorization checkpoints:
1. WebSocket connection handshake authentication and campaign viewer/reader authorization (`/ws/campaigns/{id}?user_id={user_id}`), including rejection of unauthorized subjects with 4003 codes and `PERMISSION_DENIED` frames.
2. In-session action mutators, verifying fine-grained Zanzibar object-level permissions on token movement, DM-only monster spawning and scene changes, character sheet mutations, and dynamic relation revocations.

As production SpiceDB gRPC connections and live spectator interaction channels add additional permission checks, this test file will breach 500 lines unless modularized.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Fine-grained permission checks and relationship tuple assertions.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test module separation within root test runner.
- **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: SpiceDB and gateway network boundaries.
- **ADR-0009: Continuous Backlog Refinement and Technical Debt Management**: Preemptive test splitting.

## Product & User Story References
- **Product Requirement**: [`prd-0005-realtime-websocket-board-sync.md`](../../product/accepted/prd-0005-realtime-websocket-board-sync.md)
- **User Story**: [`us-0014-realtime-board-websocket-sync.md`](../../user_stories/accepted/us-0014-realtime-board-websocket-sync.md)

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

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_websocket_zanzibar_auth.py` decomposed into focused test suites strictly under 200 lines each.
2. 100% test pass rate across all existing connection and mutator authorization tests.
3. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
4. Maintains blackbox frontdoor interactions via public WebSocket endpoints and standard domain events.
5. Passes `uv run ruff check` and `uv run pytest tests/test_websocket_zanzibar_connect_auth.py tests/test_websocket_zanzibar_mutators.py`.
