---
id: '0171'
title: Miniature Knockback Impulse and Elevation Physics
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

# TASK-0171: Miniature Knockback Impulse and Elevation Physics

## Status
Proposed

## Summary
Implement physical impulse knockback and elevation ledge falling with upright balance recovery for 3D miniature tokens in `frontend/`, snapping final rest positions to board grid coordinates.

## Problem Statement
Spell impacts, thunderwave blasts, and bull rushes currently feel purely mathematical without physical miniature knockback, sliding friction, or elevation drops.

## Governing Architecture & ADRs
- **ADR-0004: Lit + Vite Microfrontends with Storybook**: 3D tactical canvas.
- **ADR-0013: Modular Microfrontend Decomposition**: Component subviews < 200 lines.

## Scope of Work
1. **Directional Impulse Vector Application**:
   - Physics solver applying directional forces to miniature rigid bodies based on attack origins.
2. **Elevation Step & Ledge Gravity Fall**:
   - Raycast collision detection dropping miniatures down vertical elevation steps with tilt damping.
3. **Frontdoor Verification**:
   - Automated tests asserting accurate coordinate snapping to board state once momentum settles.

## Definition of Done
- Knockback solver implemented in `frontend/src/components/board/`.
- Board state mutations emit over WebSockets upon physics rest.
- Unit tests verify boundary clamping within grid dimensions.
- Component stays under 200 lines.
