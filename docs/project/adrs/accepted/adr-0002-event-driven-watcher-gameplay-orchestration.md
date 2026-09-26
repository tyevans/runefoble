# ADR-0002: Event-Driven Gameplay Architecture and The Watcher AI Engine

## Context

Runefoble combines real-time natural speech, tactical board animation, and collaborative narrative arbitration.
When a player speaks ("I move three squares north and prepare my shield"):
1. The speech must be transcribed into text without interrupting conversation flow.
2. The transcript must be analyzed for tactical intent (movement, combat, spellcasting).
3. The board state must immediately reflect valid spatial mutations.
4. The Game Master (human DM or The Watcher AI) must receive the context to arbitrate consequences.

Tight coupling or synchronous request chains between voice ingestion, board simulation, and AI narrative would create unacceptable latency and fragile state.

## Decision

We adopt an **asynchronous event-driven architecture** centered on **The Watcher AI**:

1. **CloudEvents Standard**: All domain events inherit from `BaseRunefobleEvent` (defined in `libs/runefoble_events`).
2. **Intent Parsing Pipeline**: The Watcher service listens for `PlayerSpokeEvent`, extracts structured intents, and emits reactive events (`BoardMoveEvent`, `DiceRollEvent`, `WatcherNarrationEvent`).
3. **Missing Player AI Stand-Ins**: When a participant is absent, The Watcher assigns an AI stand-in persona that mimics their character sheet traits while applying DM-inflicted penalties ("drunk", "foolishness").
4. **WebSocket Fanout**: The API Gateway subscribes to the event bus and streams state mutations to the frontend via WebSockets.

## Consequences

- Services operate independently and reactively.
- The Watcher can be swapped between autonomous mode (full AI DM) and co-pilot mode (human DM assistant).
- The tactical board reacts within milliseconds of speech parsing.
