---
id: '0883'
title: Campaign Socket Relays Actions to Owner Routes Without Gateway Policy
status: Refined
created: 2026-11-19
dependencies:
- TASK-0846
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds:
- PRD-0023
governing_stories:
- US-0065
target_release: 0.9.0
---

# TASK-0883: Campaign Socket Relays Actions to Owner Routes Without Gateway Policy

## Status
Refined

Part (b) of TASK-0846. Read the decisions in TASK-0846 first.

## Summary
The campaign socket (`gateway/api/src/gateway_api/routers/realtime.py`) applies its own action policy (`websocket_validator.py`) and publishes `runefoble.events.{action}` from client input. Replace both. Each frame names its `session_id`; the gateway checks only that the session is linked to the socket campaign, then calls the owner route for the action through the shared owner route table with the caller's token. The owner's answer (success, 403, 404) goes back to the caller as a typed frame. Unknown actions and `toggle_light` get an error frame.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)

## Detailed Specification & Implementation Plan
1. One action-to-owner-route table for the socket (no if/elif chain).
2. Remove the action policy from `websocket_validator.py` and the event publish from the socket handler.
3. Update the App Shell and UI senders to include `session_id` in each frame.
4. Update `docs/how-to/call-owning-services-through-the-gateway.md` and the WebSocket reference.

## Frontdoor Test Plan
Through the gateway socket with live loopback owners: a DM action reaches the owner and the owner event appears; a player gets the owner 403 as an error frame; a frame for a session of another campaign is refused; an unknown action gets an error frame; the gateway publishes no event.

## INVEST Criteria Evaluation
Medium. Testable through the WebSocket frontdoor.

## Definition of Done
1. Tests pass. 2. No gateway action policy and no gateway event publish remain. 3. `make health-check` passes.
