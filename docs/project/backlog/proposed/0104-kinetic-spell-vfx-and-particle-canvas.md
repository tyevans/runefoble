---
id: '0104'
title: Multi-Modal Kinetic Spell VFX & WebGL Particle Magic
status: Proposed
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
target_release: 0.4.0
prd_url: docs/project/product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md
user_story: US-0048
---

# TASK-0104: Multi-Modal Kinetic Spell VFX & WebGL Particle Magic

## Status
Proposed

## Summary
Add a high-performance WebGL particle visual effects overlay to the tactical board, translating spoken spell incantations and board actions into animated firestorms, lightning arcs, and arcane wards.

## Problem Statement
Spellcasting on digital boards lacks the visceral spectacle and dramatic punch of tabletop imagination (PRD-0016, US-0048). Performers like Nadia need spells to visually explode across the canvas with synchronized spatial audio rather than just outputting text into chat.

## Governing Architecture & ADRs
- **ADR-0004**: Lit Web Components and Storybook UI (`<runefoble-tactical-board>`).
- **ADR-0006**: Redis Streams Event Bus (`SpellCast`, `AreaEffectExploded`).
- **ADR-0012**: Accessible Dark and Light Mode Theming (high-contrast bloom shaders).
- **ADR-0013**: Microfrontend Architecture (`services/board_state/ui/`).

## Scope of Work
1. **WebGL Particle Engine**:
   - 60fps lightweight particle system handling bursts, trails, spirals, and vortexes.
2. **Spell Archetype Shader Library**:
   - Evocation (fireball explosion, lightning chain), Abjuration (runic hexagonal shield barrier), Conjuration (dimensional portal swirl).
3. **Voice-to-VFX Trigger Pipeline**:
   - Sub-150ms trigger from speech intent recognition coordinates to particle launch trajectory.
4. **Temporary Grid Decals & Cleanup**:
   - Ephemeral scorched earth or frost frostbite decals fading over rounds.
5. **Frontdoor Blackbox Verification**:
   - Blackbox test suite validating VFX trigger event serialization and board state synchronization.
