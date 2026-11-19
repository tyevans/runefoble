---
id: '0846'
title: Campaign WebSocket Actions Run Through Owner Routes
status: Refined
created: 2026-11-18
dependencies:
- TASK-0845
- TASK-0743
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: gateway
target_release: 0.9.0
---
# TASK-0846: Campaign WebSocket Actions Run Through Owner Routes

## Status
Refined

## Summary
The campaign WebSocket in the gateway builds owner event names from client input, publishes them to Redis itself, and holds the action permission policy. ADR-0015 (b) keeps the gateway thin. Hard Invariant 2 says domain events come from owners. The fix moves each action to the owner route that owns it. The owner checks permission and publishes its own events. The gateway admits the caller, forwards the action, and relays the owner result.

## Problem Statement
- `gateway/api/src/gateway_api/websocket_endpoint.py:28-33` maps action names to streams (`runefoble.events.board`, `.session`, `.watcher`).
- `websocket_endpoint.py:36-48` builds `event_type` as `runefoble.events.{action}` from the client `action` value and publishes with `publish_best_effort`. The gateway writes domain events that no owner emitted.
- `websocket_endpoint.py` (`handle_frame`, about line 91) calls `action_validator.validate_action`. The gateway decides which actions reach an owner.
- `gateway/api/src/gateway_api/websocket_validator.py:87-103` holds the action-to-permission policy. `default_action_validator` (line 105) binds SpiceDB at module level, so the policy is not injected.
- `websocket_endpoint.py` broadcasts `**data` from the client with no schema.
- `websocket_endpoint.py:129` and `websocket_validator.py:116` list `"logger"` in `__all__`. No caller imports it (DoR 9).

## Documentation & Architecture Review
- ADR-0015 (b): the gateway performs authentication, routing, and aggregation only.
- ADR-0001: object permissions run through `runefoble.zed`.
- Hard Invariant 2: domain state changes flow through aggregates and `@handles` methods.
- TASK-0845 sets one rule: a proxy route forwards the caller token, and the owner checks. This task applies the same rule to the socket.
- `docs/how-to/call-owning-services-through-the-gateway.md`, `docs/reference/events-schema.md`, `docs/reference/ports-and-endpoints.md` (WebSocket routes). Update them in the same change.

## Product & User Story References
None. Platform quality work. The App Shell frame contract does not change.

## Detailed Specification & Implementation Plan
1. Inventory. List each action in `KNOWN_ACTIONS` (move, door, light, health, condition). Name the owner route that performs it. Record the table in `docs/reference/ports-and-endpoints.md`.
2. Owner side. Each owner route checks its permission with the `runefoble.zed` relation and publishes its own domain event through its aggregate. If an owner route does not exist for an action, add it in the owning service with the same permission rule. Do not add a gateway path.
3. Gateway side. `campaign_websocket_endpoint` keeps `verify_websocket` and the `campaign.view` admission. For each frame it calls the owner route through the shared service client in `libs/`. It relays the owner status. It keeps the existing error codes (`UNKNOWN_ACTION`, `PERMISSION_DENIED`) and the existing broadcast envelope.
4. Delete `_resolve_stream` and `_publish_event` from `websocket_endpoint.py`. Delete `websocket_validator.py`. Remove `"logger"` from `__all__`. Update the import in `main.py` (line 44) if the name changes.
5. Update `tests/test_websocket_modular_decomposition.py`. It imports `WebSocketActionValidator` directly and moves with this change.
6. Size guard. If the change exceeds 15 files, split it at refinement into (a) owner routes and (b) the gateway relay, and make (b) depend on (a).

## Frontdoor Blackbox Test Plan
- Connect a stranger to `/ws/campaigns/{id}` and send `move_token`. Assert `PERMISSION_DENIED` from the owner path. Assert no event on the owner event stream.
- Connect the DM and send an allowed `modify_hp`. Assert the owner route response and the owner event (for example `character_sheet` or `game_session`). Assert the broadcast envelope is unchanged.
- Send an unknown action. Assert `UNKNOWN_ACTION`.
- Keep `tests/test_websocket_zanzibar_mutators.py` green. Update the imports in `tests/test_websocket_modular_decomposition.py`.

## Definition of Done
- The gateway publishes no domain event on the campaign socket.
- `websocket_validator.py` is deleted. No permission policy remains in `gateway/api`.
- Each action has one owner route. The table is in the reference docs.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `refactor-r2/gateways.md` (F1, F10, F12)
