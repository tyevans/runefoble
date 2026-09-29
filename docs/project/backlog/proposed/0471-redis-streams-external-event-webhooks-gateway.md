---
id: '0471'
title: Redis Streams External Domain Event Webhooks Gateway and Delivery Worker
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0001
- TASK-0008
- TASK-0015
- TASK-0016
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0011
governing_prds:
- PRD-0022
governing_stories:
- US-0008
- US-0035
target_release: 0.9.0
---

# TASK-0471: Redis Streams External Domain Event Webhooks Gateway and Delivery Worker

## Status
Proposed

## Summary
Implement an outbound domain event webhook subscription and dispatch engine in `gateway/api` allowing external bots (Discord bots, Twitch overlays, external tabletop companions, modder integrations) to receive real-time HTTP callbacks on game events (dice rolls, turn transitions, board token movements, character HP changes, and chat messages). Enforce SpiceDB Zanzibar authorization on subscription creation, sign outgoing payloads with HMAC-SHA256 headers (`X-Runefoble-Signature`), and implement asynchronous queue delivery with exponential backoff retries.

## Problem Statement
PRD-0022 specifies high-throughput Redis Streams event webhooks for external bots and community extensions. Currently, external tools and Discord bots can only inspect state via MCP or polling HTTP endpoints; they cannot register HTTP webhook endpoints to receive push notifications when domain events occur. Without an authenticated outbound webhook system, community integrations must resort to polling or maintain long-lived WebSocket connections, causing unnecessary server load and architectural fragmentation.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Authorization**: Verifying that only campaign Game Masters or owners can create, modify, or revoke webhook subscriptions.
- **ADR-0006: Redis Streams Event Bus**: Consuming domain events from consumer groups and fanning out to registered webhook endpoints.
- **ADR-0011: PostgreSQL Event Store and Persistence**: Storing webhook subscription configurations, secrets, and delivery attempt logs.

## Product & User Story References
- [`prd-0022-extensible-modder-platform-and-mcp-registry.md`](../../product/accepted/prd-0022-extensible-modder-platform-and-mcp-registry.md)
- [`us-0008-mcp-tool-invocation-for-agents.md`](../../user_stories/accepted/us-0008-mcp-tool-invocation-for-agents.md)
- [`us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md`](../../user_stories/accepted/us-0035-runtime-mcp-tool-hot-reloading-and-extension-slots.md)

## Scope of Work
1. **Webhook Subscription Models & Store (`gateway/api/src/gateway_api/models/webhooks.py`, `gateway_api/services/webhook_store.py`)**:
   - Define `WebhookSubscription` model containing `subscription_id`, `campaign_id`, `url`, `secret`, `subscribed_events` (list of CloudEvent types), `created_at`, `active`, and `last_delivery_status`.
   - Store subscriptions in persistent storage with SpiceDB permission checks (`can_manage_webhooks` / `dm` relation).
2. **Gateway Webhooks Router (`gateway/api/src/gateway_api/routers/webhooks.py`)**:
   - Provide REST endpoints:
     - `POST /api/v1/campaigns/{campaign_id}/webhooks`: Create new subscription with generated signing secret.
     - `GET /api/v1/campaigns/{campaign_id}/webhooks`: List subscriptions for campaign.
     - `DELETE /api/v1/campaigns/{campaign_id}/webhooks/{id}`: Delete subscription.
     - `POST /api/v1/campaigns/{campaign_id}/webhooks/{id}/test`: Dispatch test ping CloudEvent.
3. **Outbound Dispatch Worker (`gateway/api/src/gateway_api/workers/webhook_dispatcher.py`)**:
   - Consume Redis Streams domain events matching subscribed topics.
   - Compute HMAC-SHA256 signature using the subscription secret and attach `X-Runefoble-Signature` and `X-Runefoble-Event` headers.
   - Dispatch HTTP POST requests with a 3-second timeout and retry with exponential backoff on 5xx or connection failures.
   - Log delivery attempts and record last delivery timestamp and HTTP status code.

## Definition of Done
1. `gateway/api` exposes REST endpoints for webhook CRUD and test pings under `/api/v1/campaigns/{campaign_id}/webhooks`.
2. Outbound dispatcher subscribes to Redis Streams and sends signed CloudEvents with HMAC-SHA256 signatures.
3. SpiceDB Zanzibar authorization enforces that only campaign DMs/owners can configure webhooks.
4. All source files strictly < 200 lines per Hard Invariant 6.
5. Unit tests in `gateway/api/tests/` verify signature generation, event filtering, and retry backoff.
