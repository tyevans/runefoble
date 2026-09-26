# PRD-0003: Spatial Fog-of-War and Line-of-Sight Visibility Engine

## Status
Accepted

## Purpose
Tabletop encounters rely heavily on tactical uncertainty, surprise, and exploration. Without a robust line-of-sight and fog-of-war engine, players can metagame monster locations and map layouts. Runefoble must calculate dynamic visibility on the tactical board based on individual character perception, light sources, and vision radii, synchronizing revealed tiles between the server aggregate and Lit frontend.

## Personas & User Needs
- **Marcus (Adventurer)**: Explores dark dungeons where only tiles within torchlight or darkvision radius are revealed; concealed enemies remain shrouded until within line of sight.
- **Evelyn (Human DM)**: Toggles DM omniscient view to coordinate monster movements while preserving fog-of-war for players.
- **The Watcher (Autonomous DM)**: Evaluates visibility bounds when resolving player voice intents, preventing attacks against hidden targets in obscured cells.

## Checkable Outcomes
1. The `board_state` service calculates cell visibility maps (Chebyshev / Euclidean) given token positions, vision radii, and terrain obstructions.
2. The `<runefoble-board>` Lit component renders obscured shroud layers and hides unrevealed hostile tokens.
3. Domain events `FogOfWarRevealed`, `TerrainCellModified`, and `TokenHazardTriggered` stream across the event sourcing layer.
4. API endpoints allow configuring cell elevation, difficult terrain (2x movement budget penalty), and environmental hazards (e.g. lava triggering 2d10 damage).
5. API endpoints allow toggling fog-of-war state, setting vision radius per token, and querying visibility masks for a given party.

## Linked User Stories
- [`US-0012: Spatial Line-of-Sight and Fog-of-War Server Synchronization`](../../user_stories/accepted/us-0012-spatial-line-of-sight-and-fog-of-war.md)
- [`US-0022: Tactical Ghost Path Trajectory and Dynamic Cover Arcs`](../../user_stories/accepted/us-0022-tactical-ghost-path-and-dynamic-cover-arcs.md)

## Implementing Backlog Tasks
- [`TASK-0004: Tactical Board Fog-of-War and Token Web Component`](../../backlog/complete/0004-tactical-board-fog-of-war-web-component.md)
- [`TASK-0012: Frontend Theming System with Bauhaus Modernist Default`](../../backlog/complete/0012-frontend-theming-system-and-bauhaus-theme.md)
- [`TASK-0019: Tactical Board Terrain Elevation, Difficult Terrain & Hazard Grid`](../../backlog/complete/0019-tactical-board-terrain-elevation-hazards.md)
- [`TASK-0060: Domain Aggregates and Rule Tables Modular Decomposition`](../../backlog/complete/0060-domain-aggregates-and-rule-tables-modular-decomposition.md)
- [`TASK-0085: Board State API Router and Spatial Handler Modular Decomposition`](../../backlog/complete/0085-board-state-modular-router-decomposition.md)
