# Explanation: Realtime Voice and Tactical Board Synchronization

## Low Friction Storytelling: Speak and the Board Obeys

The goal of Runefoble is to provide the lowest friction tabletop experience in the world:
- Players should not spend game night looking down at coordinate spreadsheets or dragging tokens across screens.
- Players speak naturally: *"I charge three squares forward to intercept the skeleton."*
- The platform transcribes, extracts spatial intent, validates physics, animates the board, and updates the narrative chronicle in real time.

## Pipeline Architecture

```mermaid
sequenceDiagram
    participant Player as Player Microphone
    participant VoiceAgent as Voice Agent Service
    participant Watcher as The Watcher AI
    participant Board as Board State Engine
    participant Gateway as API Gateway (WebSocket)
    participant Client as Frontend Board UI

    Player->>VoiceAgent: Spoken Audio Stream
    VoiceAgent->>Watcher: Transcribed Text ("I move 3 squares north")
    Watcher->>Watcher: Parse Intent (Action: move, dx: 0, dy: -3)
    Watcher->>Board: Mutate Coordinates (Token: Valeros, x: 2, y: 0)
    Board-->>Watcher: Coordinates Updated & Fog of War Cleared
    Watcher->>Gateway: Broadcast Event (BoardMoveEvent + WatcherNarration)
    Gateway-->>Client: WebSocket Push
    Client->>Client: Token Animates & Chronicle Displays Ruling
```

## Latency Budgets
- **Audio Capture & Streaming**: < 100ms
- **Speech-to-Text Transcription**: < 200ms
- **Intent Parsing & Validation**: < 150ms
- **WebSocket Broadcast & Client Render**: < 50ms
- **Total Roundtrip**: < 500ms
This sub-second loop allows conversational spontaneity without noticeable lag.
