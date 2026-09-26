# US-0014: Realtime Live Board WebSocket Synchronization

## Persona
Marcus (Adventurer) / Devon (Streamer)

## User Story
As an adventurer or spectator watching the tactical grid,
I want the web frontend to connect to the Gateway WebSocket channel (`/ws/session/{session_id}`) and dynamically mirror token moves, speech actions, and Watcher chronicle entries,
So that all party members stay in lockstep without refreshing the page.

## Acceptance Criteria
1. `RunefobleApp` component connects to the Gateway WebSocket upon mounting.
2. Incoming `board_move` events update reactive token coordinates in `<runefoble-board>`.
3. Moving a token locally sends a WebSocket event to synchronize all other clients.
4. Incoming `speech_action` and `dm_ruling` events append to `<runefoble-watcher-feed>`.
5. Reconnection attempts handle socket disconnects cleanly.
