---
id: 0016
title: Live SpiceDB Zanzibar Permission Enforcement on WebSockets & Game Mutators
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0008, TASK-0010, TASK-0014]
governing_adrs: [ADR-0001, ADR-0007]
target_release: 0.1.0
---

# TASK-0016 — Live SpiceDB Zanzibar Permission Enforcement on WebSockets & Game Mutators

## Status
Complete

## Summary
Implemented fine-grained real-time SpiceDB Zanzibar authorization checks (ADR-0001, Hard Invariant 1) on WebSocket connections and game mutations (`/ws/campaigns/{campaign_id}`). When a client connects or attempts to move a token, modify character HP, apply conditions, spawn encounters, or set scenes, the gateway evaluates object-level permissions against `runefoble.zed` (`campaign:view`/`campaign:read`, `token:move`, `character:edit`, `campaign:dungeon_master`). Unauthorized actions are rejected immediately with structured `PERMISSION_DENIED` frames without mutative side-effects or event bus leakage, while authorized actions are broadcast and published to Redis Streams.

## Scope & Key Changes
1. **SpiceDB Client Enhancements (`libs/runefoble_auth/src/runefoble_auth/spicedb.py`, `__init__.py`)**:
   - Extended `SpiceDBClient` to support live SpiceDB gRPC connections via `authzed` when present, with automatic in-memory mock fallback.
   - Implemented `MockSpiceDBClient` providing offline Zanzibar tuple graph evaluation for campaigns, board tokens, and character ownership hierarchies.
   - Exported `MockSpiceDBClient` in `runefoble_auth.__all__`.
2. **WebSocket Action Validator & Connection Manager (`gateway/api/src/gateway_api/websocket.py`)**:
   - Created `WebSocketActionValidator` verifying permissions:
     - On connect: ensures subject has `campaign:view` or `campaign:read`. Unassigned subjects are greeted with `PERMISSION_DENIED` and disconnected with WebSocket code `4003`.
     - `move_token`: checks DM permissions, campaign-level `move_token`, individual `board_token:move`, and character ownership.
     - `modify_hp` / `apply_condition`: checks DM permissions or character ownership/edit relations.
     - `spawn_monster` / `set_scene`: strictly requires DM permissions (`dungeon_master`, `run_session`, `owner`).
     - Rejected actions return:
       `{"type": "error", "code": "PERMISSION_DENIED", "message": "Zanzibar authorization denied: insufficient permissions for action '<action>'", "action": action}`
       Suppressing Redis publication and party broadcasts.
     - Authorized actions publish domain events to Redis streams (`runefoble.events.board`, `runefoble.events.session`, `runefoble.events.watcher`) and broadcast state to campaign participants.
   - Implemented `CampaignWebSocketManager` managing per-campaign connection pools.
   - Maintained concise code (<250 lines, satisfying Hard Invariant 6 <400 lines).
3. **Gateway Integration (`gateway/api/src/gateway_api/main.py`)**:
   - Exposed `@app.websocket("/ws/campaigns/{campaign_id}")` wired to `campaign_websocket_endpoint`.
   - Maintained concise code (~304 lines, satisfying Hard Invariant 6 <500 lines).
4. **Comprehensive Test Suite (`tests/test_websocket_zanzibar_auth.py`)**:
   - Validated connection succeeds for subjects with `view` and `read` permissions.
   - Validated connection rejection with `PERMISSION_DENIED` error frame and WebSocket code `4003` for unassigned subjects.
   - Validated player moving their own token succeeds and dispatches broadcast.
   - Validated spectator attempting to move tokens is blocked with `PERMISSION_DENIED`.
   - Validated player attempting DM-only actions (`spawn_monster`, `set_scene`) is rejected with `PERMISSION_DENIED`.
   - Validated Dungeon Master successfully executing all actions (`move_token`, `modify_hp`, `apply_condition`, `spawn_monster`, `set_scene`).
   - Validated character owner edit permissions vs non-owner player rejections.
   - Validated Redis Streams event publication on authorized actions and suppression on unauthorized actions.
   - Validated dual mock and gRPC fallback client support.

## Verification
- `uv run pytest tests/test_websocket_zanzibar_auth.py`: 9/9 passed.
- `uv run pytest`: 136/136 passed across entire monorepo.
- `uv run ruff check .`: Clean, 0 errors.
- File length limit: all touched files strictly under 500 lines.
