---
id: 0049
title: Procedural Battlemap & Token Asset Forge Microservice
status: Proposed
created: 2026-09-25
dependencies: [TASK-0004, TASK-0007, TASK-0023]
governing_adrs: [ADR-0007, ADR-0008]
target_release: 0.3.0
---

# TASK-0049: Procedural Battlemap & Token Asset Forge Microservice

## Status
Proposed

## Summary
Scaffold a new microservice `services/asset_forge` integrating diffusion and segmentation pipelines to generate procedural battlemaps with automated wall/hazard geometry extraction saved to Silo S3.

## Problem Statement
Finding, formatting, and drawing line-of-sight walls on battlemaps consumes hours of DM prep time. DMs need spoken or prompted map generation that immediately yields game-ready tactical grids.

## Scope of Work
1. **Service Scaffolding**: Create `services/asset_forge` in UV monorepo.
2. **Generative Model Integration**: Interface with local or cloud image generation models for top-down battlemaps and character tokens.
3. **Automated Wall & Obstacle Segmentation**: Extract solid barriers and difficult terrain contours, serializing them into `board_state` wall segments.
4. **Silo S3 Storage Pipeline**: Persist generated image artifacts directly into MinIO/Silo buckets.

## Acceptance Criteria
1. Generates 2K battlemap texture from prompt within 15 seconds.
2. Automatically generates valid line-of-sight wall segments pushed to `board_state`.
3. Stores all generated image assets in Silo S3 with valid presigned URLs.
