# TASK-0007: Board Fog-of-War Spatial Visibility and Shroud Synchronization

## Description
Extend `services/board_state` and `BoardAggregate` with server-side spatial visibility calculations, dynamic fog-of-war masks based on token vision radii, and shroud synchronization. Publish domain events when tokens move and reveal uncharted grid coordinates.

## Governing Documents
- ADRs: ADR-0002, ADR-0007, ADR-0011
- PRDs: PRD-0001, PRD-0003
- User Stories: US-0001, US-0012

## Definition of Done
1. `BoardAggregate` tracks `vision_radius` per token and computes an 8-way Chebyshev visibility grid.
2. The aggregate exposes a command/method to compute revealed cells for a given party perspective.
3. `/api/v1/board/visibility` endpoint returns active vision masks and revealed coordinates.
4. Moving a token updates revealed cells and publishes `FogOfWarRevealedEvent` over Redis Streams.
5. Unit and property tests verify visibility boundaries, obstruction calculations, and event sourcing.
