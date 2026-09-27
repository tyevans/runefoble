---
id: '0104'
title: Multi-Modal Kinetic Spell VFX & WebGL Particle Magic
status: Refined
created: 2026-09-26
dependencies:
- TASK-0004
- TASK-0039
- TASK-0084
governing_adrs:
- ADR-0004
- ADR-0006
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0016
governing_stories:
- US-0048
target_release: 0.4.0
---

# TASK-0104: Multi-Modal Kinetic Spell VFX & WebGL Particle Magic

## Status
Refined

## Summary
Add a high-performance WebGL particle visual effects overlay to the tactical board, translating spoken spell incantations and board actions into animated firestorms, lightning arcs, and arcane wards.

## Problem Statement
Spellcasting on digital boards lacks the visceral spectacle and dramatic punch of tabletop imagination (PRD-0016, US-0048). Performers like Nadia need spells to visually explode across the canvas with synchronized spatial audio rather than just outputting text into chat.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated WebGL particle overlay within `<runefoble-tactical-board>`.
- **ADR-0006: Redis Streams Event Bus**: Event dispatch for `SpellCast`, `AreaEffectExploded`, and `VFXAnimationFinished`.
- **ADR-0012: Accessible Dark and Light Mode Theming**: Dynamic particle bloom luminance and contrast calibration across themes.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Particle shader module housed in `services/board_state/ui/src/`.

## Product & User Story References
- **Product Requirement**: [`prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md`](../../product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md)
- **User Story**: [`us-0048-kinetic-spell-vfx-and-particle-canvas.md`](../../user_stories/accepted/us-0048-kinetic-spell-vfx-and-particle-canvas.md)

## Detailed Specification & Implementation Plan
1. **WebGL Particle Engine (`services/board_state/ui/src/particle_canvas.ts`)**:
   - 60fps lightweight particle system handling bursts, trails, spirals, and vortexes.
   - Instanced particle rendering maintaining low GPU footprint across mobile and desktop.
2. **Spell Archetype Shader Library**:
   - Evocation (fireball explosions, lightning chain arcs).
   - Abjuration (runic hexagonal shield barrier, deflection ripples).
   - Conjuration (dimensional portal swirl, mist clouds).
3. **Voice-to-VFX Trigger Pipeline**:
   - Sub-150ms trigger from speech intent recognition coordinates to particle launch trajectory.
4. **Temporary Grid Decals & Natural Cleanup**:
   - Ephemeral scorched earth or frost decals fading over 2 rounds without permanent board clutter.
5. **Frontdoor Blackbox Verification**:
   - Blackbox test suite validating VFX trigger event serialization and board state synchronization.

## INVEST Criteria Evaluation
- **Independent (I)**: Decoupled visual layer rendering on top of existing grid coordinates.
- **Negotiable (N)**: Particle density and decay curves can be adjusted for performance.
- **Valuable (V)**: Delivers tactile, visceral magical feedback to voice commands and spellcasting.
- **Estimable (E)**: Follows existing tactile board kinematics patterns (TASK-0084).
- **Small (S)**: Scope strictly isolated to `services/board_state/ui/`; all files < 300 lines.
- **Testable (T)**: Frontdoor tests verify event schemas and canvas shader instantiation.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **WebGL Particle Overlay**:
   - Integrated into `<runefoble-tactical-board>` with automatic canvas resizing and zero layout shift.
2. **Spell Archetypes**:
   - Fireball, Lightning Arc, and Arcane Shield particle shaders rendering at 60fps.
3. **Storybook Stories**:
   - Stories showcasing firestorm, lightning, and shield barrier animations with interactive trigger buttons.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_spell_vfx.py` verifying spell trigger events and board animation state via public routes.
5. **Quality Gates**:
   - Conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `pnpm run build` and `uv run pytest tests/test_blackbox_spell_vfx.py`.
