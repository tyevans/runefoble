---
id: 0009
title: Procedural Battlemap & Token Asset Generation Engine
status: Shipped
created: 2026-09-25
---

# PRD-0009 — Procedural Battlemap & Token Asset Generation Engine

## Who this is for

Human Dungeon Masters (Evelyn) facing hours of map preparation, and players (Marcus) wanting unique character avatars without external art commissions.

## What the person cannot do today

Creating or purchasing battlemaps, sizing grid alignments, drawing line-of-sight walls, and sourcing matching character tokens is one of the heaviest time sinks in virtual tabletop gaming.

## What good looks like

- **Spoken / Prompted Battlemap Generation**: DMs can speak or type descriptions (*"Subterranean dwarven forge with lava canals and broken anvil statues"*), generating high-resolution grid maps saved directly to Silo S3.
- **Automated Spatial Wall & Hazard Geometry Extraction**: The engine automatically detects solid obstacles (walls, pillars) and difficult terrain/hazards (water, lava), projecting collision data directly into `board_state`.
- **Character & Monster Portrait Forge**: Generates stylistic tokens and avatars matching the campaign's visual aesthetic with transparent backgrounds.

## What this does not do

- It does not replace manually created human battlemaps; users can still upload standard `.png`, `.jpg`, or `.dd2vtt` files.
- It does not generate non-functional maps; every generated map includes validated grid and wall geometry.

## What it costs at scale

GPU inference cycles for diffusion and segmentation pipelines; results are aggressively cached in Silo S3.

## Checkable Outcomes

1. Battlemap prompt generates a 2K textured map and uploads it to Silo S3 within 15 seconds.
2. Wall segments, doors, and hazard boundaries are automatically extracted and pushed to `board_state`.
3. Character portrait generation produces cropped circular tokens formatted for frontend canvas rendering.

## Linked User Stories
- [`US-0033: Universal VTT Map Importer and Scriptable Grid Tiles`](../../user_stories/accepted/us-0033-universal-vtt-map-importer-and-scriptable-tiles.md)
- [`US-0038: Generative Procedural Battlemaps and Character Portraits`](../../user_stories/accepted/us-0038-generative-procedural-battlemaps-and-tokens.md)

## Implementing Backlog Tasks
- [`TASK-0049: Procedural Battlemap & Token Asset Forge Microservice`](../../backlog/complete/0049-procedural-battlemap-and-asset-forge-bc.md)
- [`TASK-0057: Universal VTT Importer and Dynamic MCP Tool Registry`](../../backlog/complete/0057-universal-vtt-importer-and-custom-mcp-tool-registry.md)
- [`TASK-0067: Silo S3 Media Asset Bucket Storage and Battlemap Pipeline Test Suite Modular Decomposition`](../../backlog/complete/0067-silo-assets-and-battlemap-test-suite-decomposition.md)
- [`TASK-0078: Battlemap Uploader Subviews and Grid Controller Modular Decomposition`](../../backlog/complete/0078-battlemap-uploader-subviews-and-grid-controller-decomposition.md)
- [`TASK-0092: Asset Forge Blackbox Test Suite Modular Decomposition`](../../backlog/complete/0092-asset-forge-test-suite-modular-decomposition.md)
