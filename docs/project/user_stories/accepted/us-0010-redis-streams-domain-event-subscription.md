---
id: 0010
title: Redis Streams Distributed Domain Event Subscription
status: Accepted
created: 2026-09-25
persona: Alex (The Developer / Plugin Modder)
feature: FEAT-DEV-03
governing_prd: PRD-0005
---

# US-0010 — Redis Streams Distributed Domain Event Subscription

## Governing PRD
- [`PRD-0005: Real-Time WebSocket Board & Chronicle Synchronization`](../../product/accepted/prd-0005-realtime-websocket-board-sync.md)

## User Story

**As a** backend service or external plugin developer,
**I want** to consume platform domain events (speech transcripts, token movements, dice rolls, penalties) asynchronously via Redis Streams consumer groups,
**So that** my microservices react to gameplay changes with guaranteed delivery and zero inter-service tight coupling.

## Scenario: Consuming Board Move Events
```gherkin
Given a consumer group "board-animator-group" listening on stream "runefoble.events.board"
When The Watcher emits a "board.move" event with token coordinates
Then Redis Streams delivers the event to an active consumer in the group
And the consumer processes the spatial update and acknowledges with XACK
And the API Gateway broadcasts the update to client WebSockets.
```
