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
