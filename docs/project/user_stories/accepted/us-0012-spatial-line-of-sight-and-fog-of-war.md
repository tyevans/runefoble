# US-0012: Spatial Line-of-Sight and Fog-of-War Server Synchronization

## Persona
Evelyn (Human DM) / Marcus (Adventurer)

## User Story
As a player or DM moving tokens across the tactical grid,
I want the server `board_state` service to compute which cells are shrouded in fog-of-war based on player token vision radii,
So that unrevealed dungeon terrain and lurking hostile tokens are filtered out from player view while remaining visible to the DM.

## Acceptance Criteria
1. `BoardAggregate` tracks vision radii per token and computes an 8-way Chebyshev visibility matrix.
2. The endpoint `/api/v1/board/visibility` returns revealed coordinate arrays for a given party or player perspective.
3. Hostile tokens in shrouded cells are omitted from player board updates unless revealed by party line of sight.
4. Moving a token publishes a `CellShroudUpdatedEvent` across Redis Streams.
