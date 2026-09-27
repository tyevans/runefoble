---
id: '0191'
title: Kinetic Spell VFX Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0104
- TASK-0132
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0016
governing_stories:
- US-0048
target_release: 0.7.0
---

# TASK-0191: Kinetic Spell VFX Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_spell_vfx.py` (342 lines, 68.4% of limit) into modular focused sub-suites under `tests/test_blackbox_spell_vfx/` (`test_spell_adjudication.py`, `test_decals_and_lifecycle.py`, `test_speech_vfx_triggers.py`, `test_particle_contracts.py`), keeping all test modules strictly < 150 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_spell_vfx.py` contains 342 lines testing REST spellcasting endpoints, Evocation/Abjuration/Conjuration archetypes, ephemeral decal decay over rounds, real-time WebSocket speech triggers, domain event sourcing replay, and particle canvas module contracts. As Milestone 9 adds rotatable AoE templates and elevation physics, this test file risks surpassing 400 lines unless decomposed into modular test suites.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular test package structure.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain separation between spell adjudication, board decals, and particle VFX pipelines.
- **ADR-0010: Real-Time WebSocket Board Synchronization**: Sub-150ms speech-to-VFX latency validation.
- **ADR-0013: Microfrontend Bounded Context Architecture**: UI element and Storybook contract verification.

## Scope of Work
1. **Modular Test Package (`tests/test_blackbox_spell_vfx/`)**:
   - `test_spell_adjudication.py`: REST spellcasting endpoints, Evocation/Abjuration/Conjuration archetypes, trajectory generation, and SLA latency verification (< 120 lines).
   - `test_decals_and_lifecycle.py`: Ephemeral decal decay over rounds, fading opacity, and animation finished callbacks (< 100 lines).
   - `test_speech_vfx_triggers.py`: Real-time WebSocket speech-to-VFX triggers, sub-150ms broadcast SLA, and event sourcing domain events persistence (< 110 lines).
   - `test_particle_contracts.py`: Microfrontend components, Storybook stories, and modular particle canvas / projectile / decal contracts (< 80 lines).
2. **Backward Compatibility**:
   - Maintain `tests/test_blackbox_spell_vfx.py` as a lightweight re-exporting test shim (< 40 lines).
3. **Verification**:
   - Run `uv run pytest tests/test_blackbox_spell_vfx/` and verify all tests pass.

## Definition of Done
- `tests/test_blackbox_spell_vfx.py` decomposed into focused sub-suites under `tests/test_blackbox_spell_vfx/`.
- All test files strictly < 150 lines.
- All spell VFX blackbox tests pass via `uv run pytest`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
