# PRD-0005: Real-Time WebSocket Board & Chronicle Synchronization

## Status
Accepted

## Purpose
Tabletop roleplaying requires sub-second synchronization between player actions, DM rulings, voice transcripts, and board tokens across all connected browsers. When a player speaks or drags a token, every party member and spectator must observe the movement and chronicle update immediately.

## Personas & User Needs
- **Marcus (Adventurer)**: Speaks or moves his token; sees all other party tokens animate simultaneously with zero manual browser refreshing.
- **Devon (Spectator/Streamer)**: Watches the live feed without latency, receiving board state mutations and Watcher narration in real-time.
- **Evelyn (Human DM)**: Receives immediate socket broadcasts of player intent interpretations and roll outcomes.

## Checkable Outcomes
1. The API Gateway `/ws/session/{session_id}` endpoint broadcasts structured board events: `token_moved`, `speech_action`, `fog_revealed`, `turn_advanced`.
2. The Lit application in `frontend/src/runefoble-app.ts` initiates a WebSocket connection to the gateway and handles incoming events to dynamically update reactive board tokens and the Watcher feed.
3. If disconnected, the frontend gracefully exhibits a reconnecting state without crashing.
4. Storybook and unit tests verify event serialization and reception.

## Linked User Stories
- [`US-0010: Redis Streams Distributed Domain Event Subscription`](../../user_stories/accepted/us-0010-redis-streams-domain-event-subscription.md)
- [`US-0014: Realtime Live Board WebSocket Synchronization`](../../user_stories/accepted/us-0014-realtime-board-websocket-sync.md)

## Implementing Backlog Tasks
- [`TASK-0010: Real-time WebSocket Protocol & Client Board Sync`](../../backlog/complete/0010-realtime-websocket-client-board-sync.md)
- [`TASK-0014: Real-Time Spectator Stream & Chronicle Clean Overlay`](../../backlog/complete/0014-realtime-spectator-stream-clean-overlay.md)
- [`TASK-0015: Distributed Redis Streams Consumer Groups & Event Projection Workers`](../../backlog/complete/0015-redis-streams-consumer-groups-projections.md)
- [`TASK-0071: WebSocket Zanzibar Authorization and Mutator Test Suite Modular Decomposition`](../../backlog/complete/0071-websocket-zanzibar-auth-test-suite-decomposition.md)
- [`TASK-0080: Gateway WebSocket Hub and Action Validator Modular Decomposition`](../../backlog/complete/0080-gateway-websocket-hub-and-action-validator-decomposition.md)
