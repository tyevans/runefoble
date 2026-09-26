---
id: '0080'
title: Gateway WebSocket Hub and Action Validator Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0010, TASK-0016, TASK-0034, TASK-0035]
governing_adrs: [ADR-0001, ADR-0005, ADR-0007]
target_release: 0.2.0
---

# TASK-0080: Gateway WebSocket Hub and Action Validator Modular Decomposition

## Status
Proposed

## Summary
Decompose `gateway/api/src/gateway_api/websocket.py` (336 lines, 67.2% of limit) into modular components separating the SpiceDB Zanzibar action validation policy engine (`websocket_validator.py`), client connection manager (`websocket_manager.py`), and the WebSocket routing endpoint handler (`websocket_endpoint.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
`gateway/api/src/gateway_api/websocket.py` currently couples three distinct concerns:
1. `WebSocketActionValidator`: Fine-grained SpiceDB Zanzibar permission checks for connection admission, DM role verification, token movement authorization, monster spawning guards, and character sheet edits.
2. `CampaignConnectionManager`: Connection registry, connection state tracking, channel broadcasting, and error handling for active sockets.
3. `campaign_websocket_endpoint`: WebSocket handshake handling, token query parameter/subprotocol extraction, heartbeat ping-pong loops, incoming JSON message dispatch, and disconnect cleanup.

With upcoming real-time features including voice room signaling integrations, spectator chat relays, and collaborative dice roll broadcasts, `websocket.py` will soon breach the 500-line invariant if left as a monolithic module.

## Proposed Decomposition
1. **Zanzibar Action Validator (`gateway/api/src/gateway_api/websocket_validator.py`)**:
   - Encapsulate `WebSocketActionValidator` with permission checks against SpiceDB Zanzibar schema (< 140 lines).
2. **Connection Hub Manager (`gateway/api/src/gateway_api/websocket_manager.py`)**:
   - Encapsulate `CampaignConnectionManager` tracking active clients and broadcasting messages (< 100 lines).
3. **Endpoint & Lifecycle Handler (`gateway/api/src/gateway_api/websocket.py`)**:
   - Retain `campaign_websocket_endpoint` and re-export `WebSocketActionValidator` and `CampaignConnectionManager` for backward compatibility (< 130 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal WebSocket gateway structure without changing external WebSocket paths (`/ws/campaigns/{id}`), frame protocols, or Zanzibar schema checks.
- **Negotiable (N)**: Distribution of connection registry helpers can be adapted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and creates clean separation between authorization rules and socket I/O.
- **Estimable (E)**: Standard refactoring extracting classes into dedicated modules with clean re-exports.
- **Small (S)**: Scope strictly isolated to `gateway/api/src/gateway_api/websocket.py`; all resulting files < 150 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_websocket_*.py tests/test_blackbox_zitadel_auth.py`.

## Acceptance Criteria
1. `gateway/api/src/gateway_api/websocket.py` decomposed into modular files strictly under 150 lines each.
2. 100% test pass rate across all WebSocket test suites.
3. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
4. Zero breaking changes to client WebSocket protocols or permission validation behaviors.
