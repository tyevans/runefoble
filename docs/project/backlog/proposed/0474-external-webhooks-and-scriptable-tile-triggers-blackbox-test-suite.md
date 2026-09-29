---
id: '0474'
title: External Webhooks and Scriptable Tile Triggers Blackbox Test Suite
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0470
- TASK-0471
- TASK-0472
- TASK-0473
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0008
governing_prds:
- PRD-0022
governing_stories:
- US-0008
- US-0033
- US-0035
target_release: 0.9.0
---

# TASK-0474: External Webhooks and Scriptable Tile Triggers Blackbox Test Suite

## Status
Proposed

## Summary
Implement a comprehensive end-to-end blackbox test suite (`tests/test_blackbox_webhooks_and_tile_triggers.py`) verifying the complete lifecycle of Universal VTT scriptable tile triggers, Redis Streams event propagation, outbound webhook deliveries with HMAC-SHA256 signature verification, and FastMCP streaming resource endpoints through public frontdoor interfaces without backdoor state manipulation.

## Problem Statement
While individual unit tests verify component details, the interaction between Universal VTT map ingestion, board token movement evaluation, `TileTriggerActivated` CloudEvents, Redis Streams fan-out, and outbound HMAC-signed HTTP webhook dispatching must be rigorously validated through public frontdoor APIs to satisfy Hard Invariant 7. Without an automated blackbox suite, regressions in event serialization or webhook delivery backoff cannot be caught prior to deployment.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Authorization**: Verifying permission enforcement for webhook registration and board mutations through frontdoor JWT tokens.
- **ADR-0006: Redis Streams Event Bus**: End-to-end event propagation from board movement to webhook HTTP POST dispatch.
- **ADR-0008: FastMCP Gateway Architecture**: Frontdoor validation of MCP resource reading.

## Product & User Story References
- [`prd-0022-extensible-modder-platform-and-mcp-registry.md`](../../product/accepted/prd-0022-extensible-modder-platform-and-mcp-registry.md)
- [`us-0008-mcp-tool-invocation-for-agents.md`](../../user_stories/accepted/us-0008-mcp-tool-invocation-for-agents.md)
- [`us-0033-universal-vtt-map-importer-and-scriptable-tiles.md`](../../user_stories/accepted/us-0033-universal-vtt-map-importer-and-scriptable-tiles.md)
- [`us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md`](../../user_stories/accepted/us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md)

## Scope of Work
1. **Blackbox Webhook Registration & Delivery Test (`tests/test_blackbox_webhooks_and_tile_triggers.py`)**:
   - Register external webhook subscription via Gateway API (`POST /api/v1/campaigns/{campaign_id}/webhooks`).
   - Spawn a mock local HTTP receiver to capture outbound webhook POST requests.
   - Trigger a dice roll or token movement via frontdoor API; assert mock receiver receives signed CloudEvent with valid HMAC-SHA256 signature header.
2. **Scriptable Tile Trigger Frontdoor Test**:
   - Ingest a `.dd2vtt` map containing a scriptable teleporter tile.
   - Execute token move into triggered coordinates via `POST /api/v1/board/{id}/tokens/{token_id}/move`.
   - Assert token position is immediately translated to teleporter target coordinates and `TileTriggerActivated` event is published.
3. **FastMCP Resource Streaming Verification**:
   - Query `session://{session_id}/transcript` and `session://{session_id}/initiative` via FastMCP client, verifying real-time data payload format.
4. **Zanzibar Security Guardrail Assertions**:
   - Assert non-DM / non-owner players receive 403 Forbidden when attempting to register or delete campaign webhooks.

## Definition of Done
1. `tests/test_blackbox_webhooks_and_tile_triggers.py` implemented using strictly public frontdoors.
2. Asserts webhook HMAC signature validity and delivery retry behavior.
3. Asserts scriptable tile trigger kinematics and event publishing.
4. Test suite conforms strictly to Hard Invariant 6 (< 350 lines).
5. Passes `uv run pytest tests/test_blackbox_webhooks_and_tile_triggers.py` and lint checks.
