---
id: 0033
title: Universal VTT Map Importer and Scriptable Grid Tiles
status: Accepted
created: 2026-09-25
governing_prd: PRD-0009
---

# US-0033 — Universal VTT Map Importer and Scriptable Grid Tiles

## Governing PRD
- [`PRD-0009: Procedural Battlemap & Token Asset Generation Engine`](../../product/accepted/prd-0009-procedural-battlemap-and-token-asset-generation.md)

## User Story

**As a** homebrew creator and technical DM (Alex),  
**I want to** import maps using standard Universal VTT formats and write custom scripts for grid tiles,  
**So that** I can reuse existing community battlemaps and create complex interactive puzzles and moving hazards.

## Acceptance Criteria

1. **Universal VTT (.dd2vtt) Importer**: Parses image layers, grid scaling, wall blockers, and light sources into `board_state` schemas.
2. **Scriptable Tile Triggers**: Allows attaching declarative logic (e.g. teleporters, pressure plates, sliding floors) to specific board coordinates.
3. **Event Bus Integration**: Tile trigger executions emit standard `TileTriggerActivated` CloudEvents over Redis Streams.
