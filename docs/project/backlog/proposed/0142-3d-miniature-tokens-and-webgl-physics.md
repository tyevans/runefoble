---
id: '0142'
title: 3D Miniature Tokens & WebGL Tabletop Physics
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0004
- TASK-0017
- TASK-0104
- TASK-0150
governing_adrs:
- ADR-0013
governing_prds:
- PRD-0013
governing_stories:
- US-0061
target_release: 0.6.0
---

# TASK-0142: 3D Miniature Tokens & WebGL Tabletop Physics

## Status
Proposed

## Summary
Introduce 3D WebGL miniature tokens with physical dice rolling and terrain collision physics on the tactical board, allowing tokens and tumbling dice to interact with walls, pillars, and elevation changes.

## Problem Statement
While 2D board kinematics (TASK-0084) and WebGL particle VFX (TASK-0104) provide rich visual feedback, streamers and players desire tactile 3D miniatures that react to physical impacts, knockbacks, and bouncing physical dice.

## Governing Architecture & ADRs
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Three.js WebGL canvas wrapper in `services/board_state/ui/src/`.

## Scope of Work
1. **3D Miniature Token Mesh Generator**:
   - Extrude 2D circular tokens into stylized 3D miniature bases with character portraits and status rings (< 180 lines).
2. **Tabletop Physics Simulation**:
   - Connect client-side rendering with backend physics engine (TASK-0150) calculating dice bounces and miniature knockback collisions (< 180 lines).
3. **Terrain Elevation Integration**:
   - Dynamic 3D meshes generated from grid elevation and hazard parameters (< 160 lines).
4. **Frontdoor Verification**:
   - Blackbox tests and Storybook stories demonstrating physical dice tray collisions and 3D token positioning.
