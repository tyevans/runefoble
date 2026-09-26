---
id: 0038
title: Generative Procedural Battlemaps and Character Portraits
status: Shipped
created: 2026-09-25
---

# US-0038 — Generative Procedural Battlemaps and Character Portraits

## User Story

**As a** DM and player creating custom tabletop environments (Evelyn and Marcus),  
**I want to** synthesize tactical battlemaps and character tokens from text prompts,  
**So that** we have instant, beautiful visuals for any encounter without external artistic preparation.

## Acceptance Criteria

1. **Text-to-Battlemap Generation**: Renders high-resolution battlemaps from natural language prompts within 15 seconds.
2. **Automated Grid & Wall Extraction**: Computes tactical grid alignment and solid wall collision boundaries automatically.
3. **Token Portrait Synthesis**: Generates circular character and creature tokens with transparent alpha channels saved directly to Silo S3.
