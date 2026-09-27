---
id: '0170'
title: Kinetic 3D Dice Physics and Tray Audio Integration
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0150
- TASK-0142
governing_adrs:
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0021
governing_stories:
- US-0061
target_release: 0.7.0
---

# TASK-0170: Kinetic 3D Dice Physics and Tray Audio Integration

## Status
Proposed

## Summary
Integrate 3D polyhedral rigid-body dice collisions with Cannon-es physics and synchronized WebAudio acoustic tray clatter in `frontend/`, matching settled dice faces to server-side cryptographic rolls.

## Problem Statement
Flat random number generators lack the tactile drama, visual anticipation, and shared suspense of physical polyhedral dice tumbling across terrain and bouncing off obstacles.

## Governing Architecture & ADRs
- **ADR-0004: Lit + Vite Microfrontends with Storybook**: WebGL canvas components.
- **ADR-0013: Modular Microfrontend Decomposition**: Component subviews < 200 lines.

## Scope of Work
1. **Cannon-es Polyhedral Rigid Bodies**:
   - Collision geometries for d4, d6, d8, d10, d12, and d20 dice with restitution, mass, and friction parameters.
2. **Impact Clatter Spatial Audio**:
   - WebAudio synthesis trigger playing velocity-scaled acoustic tray clatter on wall and floor bounces.
3. **Frontdoor Verification**:
   - Automated physics tests verifying that resting dice faces agree with cryptographic server results on 100% of rolls.

## Definition of Done
- 3D dice physics component integrated in `frontend/src/components/board/`.
- Canvas rendering maintains steady 60fps on standard desktop browsers.
- Storybook visual demonstration of dice rolls.
- Component stays under 250 lines.
