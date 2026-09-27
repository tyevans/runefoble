---
id: '0132'
title: Particle Canvas Decals and Projectile Physics Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0104
governing_adrs:
- ADR-0004
- ADR-0006
- ADR-0012
- ADR-0013
target_release: 0.4.0
governing_prds:
- PRD-0016
governing_stories:
- US-0048
pr_url: https://github.com/tyevans/runefoble/pull/139
---
# TASK-0132: Particle Canvas Decals and Projectile Physics Modular Decomposition

## Status
Refined

## Summary
Decompose `services/board_state/ui/src/particle_canvas.ts` (492 lines, 98.4% of limit) by extracting projectile trajectory calculation and ephemeral grid decal decay handling into dedicated modules (`particle_projectiles.ts` and `particle_decals.ts`), ensuring the particle canvas engine stays comfortably under 300 lines and guarding against breaches of Hard Invariant 6 (< 500 lines).

## Problem Statement
`services/board_state/ui/src/particle_canvas.ts` currently spans 492 lines following the implementation of TASK-0104. It manages WebGL rendering context setup, 2D fallback rendering, active particle lifecycles, projectile ballistic arcs and parabolic trajectories, and combat grid decal rendering and opacity decay in a single monolithic class. At 492 lines, any future spell visual effect or configuration option will breach Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Strict Shadow DOM encapsulation and modular WebGL helper structure.
- **ADR-0006: Redis Streams Event Bus**: Event dispatch alignment for projectile arrival and decal expiration.
- **ADR-0012: Accessible Dark and Light Mode Theming**: Bloom luminance and contrast calculation separation.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Tactical board UI assets isolated in `services/board_state/ui/src/`.

## Product & User Story References
- **Product Requirement**: [`prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md`](../../product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md)
- **User Story**: [`us-0048-kinetic-spell-vfx-and-particle-canvas.md`](../../user_stories/accepted/us-0048-kinetic-spell-vfx-and-particle-canvas.md)

## Detailed Specification & Implementation Plan
1. **Projectile Physics Engine (`services/board_state/ui/src/particle_projectiles.ts`)**:
   - Extract `ActiveProjectile` state tracking, parabolic arc interpolation, and collision check helpers (< 140 lines).
2. **Decal Management Engine (`services/board_state/ui/src/particle_decals.ts`)**:
   - Extract `EphemeralDecal` rendering, 2D/WebGL billboard drawing, and opacity decay curves (< 140 lines).
3. **Core Particle Engine Streamlining (`services/board_state/ui/src/particle_canvas.ts`)**:
   - Focus `WebGLParticleEngine` exclusively on WebGL program initialization, buffer management, and main animation loop (< 250 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Isolated to `services/board_state/ui/src/` internal TypeScript modules with zero cross-service coupling.
- **Negotiable (N)**: Split granularity between projectiles and decals can be tailored during refactoring.
- **Valuable (V)**: Eliminates risk of breaching Hard Invariant 6 on the largest frontend file (492 lines) in the repo.
- **Estimable (E)**: Pure refactoring with well-defined interfaces and zero domain logic changes.
- **Small (S)**: Single-pass decomposition creating two helper files (<140 lines each) and reducing `particle_canvas.ts` to <250 lines.
- **Testable (T)**: Validated via frontend test suite and blackbox spell VFX test suite (`tests/test_blackbox_spell_vfx.py`).

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Extraction**:
   - `services/board_state/ui/src/particle_projectiles.ts` and `services/board_state/ui/src/particle_decals.ts` extracted with full TypeScript types.
2. **Line Count Invariant**:
   - `services/board_state/ui/src/particle_canvas.ts` reduced to < 260 lines.
   - All extracted files strictly < 200 lines.
3. **Zero Functional Regressions**:
   - Particle trajectories, ballistic arcs, and decal decay render seamlessly in Storybook and microfrontend board views.
4. **Verification Gates**:
   - `pnpm run build` succeeds without TypeScript/Vite compilation errors.
   - `uv run pytest tests/test_blackbox_spell_vfx.py` passes 100%.
   - `python3 scripts/health_check.py` reports zero files exceeding 500 lines.
