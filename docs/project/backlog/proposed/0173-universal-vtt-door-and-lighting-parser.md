---
id: '0173'
title: Universal VTT Door and Dynamic Lighting Parser
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0057
governing_adrs:
- ADR-0003
- ADR-0006
governing_prds:
- PRD-0022
governing_stories:
- US-0033
target_release: 0.7.0
---

# TASK-0173: Universal VTT Door and Dynamic Lighting Parser

## Status
Proposed

## Summary
Extend Universal VTT (`.uvtt` / `.dd2vtt`) parser in `services/board_state/` to extract interactive door geometries, secret portal triggers, and ambient point-light sources into native fog-of-war layers.

## Problem Statement
While basic UVTT wall extraction works, doors and light sources are currently dropped, forcing DMs to manually re-author dynamic lighting and interactive doors on imported community maps.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular parsing in `board_state`.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Board illumination mutations.

## Scope of Work
1. **Door & Secret Portal Geometry Extraction**:
   - Parse door line segments, swing pivot metadata, and locked/unlocked state flags.
2. **Point Light & Color Radiance Modeling**:
   - Map UVTT light entities (color hex, dim radius, bright radius) to board illumination models.
3. **Frontdoor Verification**:
   - Blackbox tests asserting 100% geometric extraction accuracy against standard sample UVTT test assets.

## Definition of Done
- Parser module integrated in `services/board_state/src/board_state/`.
- Board state reflects doors and light sources in WebSocket payloads.
- Unit tests pass with `uv run pytest`.
- File length remains under 200 lines.
