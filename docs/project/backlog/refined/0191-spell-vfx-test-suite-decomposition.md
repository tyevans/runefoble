---
id: '0191'
title: Kinetic Spell VFX Blackbox Test Suite Modular Decomposition
status: Refined
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
Refined

## Summary
Decompose `tests/test_blackbox_spell_vfx.py` (342 lines, 68.4% of limit) into modular focused sub-suites under `tests/test_blackbox_spell_vfx/` (`conftest.py`, `test_spell_adjudication.py`, `test_decals_and_lifecycle.py`, `test_speech_vfx_triggers.py`), keeping all test modules strictly < 150 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_spell_vfx.py` contains 342 lines testing REST spellcasting endpoints, Evocation/Abjuration/Conjuration archetypes, ephemeral decal decay over rounds, real-time WebSocket speech triggers, domain event sourcing replay, and particle canvas module contracts in a single file. As Milestone 9 adds rotatable AoE templates and elevation physics, this test file risks surpassing 400 lines unless decomposed into modular test suites.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular test package structure.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain separation between spell adjudication, board decals, and particle VFX pipelines.
- **ADR-0010: Real-Time WebSocket Board Synchronization**: Sub-150ms speech-to-VFX latency validation.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: UI element and Storybook contract verification.

## Detailed Specification & Implementation Plan
1. **Shared Fixtures (`tests/test_blackbox_spell_vfx/conftest.py`)**:
   - Extract test client, mock Redis bus, particle canvas fixtures, and spell templates (< 60 lines).
2. **Spell Adjudication Tests (`tests/test_blackbox_spell_vfx/test_spell_adjudication.py`)**:
   - REST spellcasting endpoints, Evocation/Abjuration/Conjuration archetypes, trajectory generation, and SLA latency verification (< 120 lines).
3. **Decals & Lifecycle Tests (`tests/test_blackbox_spell_vfx/test_decals_and_lifecycle.py`)**:
   - Ephemeral decal decay over rounds, fading opacity, and animation finished callbacks (< 100 lines).
4. **Speech-to-VFX Triggers Tests (`tests/test_blackbox_spell_vfx/test_speech_vfx_triggers.py`)**:
   - Real-time WebSocket speech-to-VFX triggers, sub-150ms broadcast SLA, and event sourcing domain events persistence (< 110 lines).
5. **Verification**:
   - Remove root test module `tests/test_blackbox_spell_vfx.py` and run `uv run pytest tests/test_blackbox_spell_vfx/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Test refactoring isolated entirely to the `tests/test_blackbox_spell_vfx/` package.
- **Negotiable (N)**: Test categories separate spell adjudication, decal lifecycles, and real-time speech triggers.
- **Valuable (V)**: Safeguards against Hard Invariant 6 (500 lines) and speeds up test isolation for VFX bugs.
- **Estimable (E)**: Deterministic extraction of test cases into discrete test modules with shared `conftest.py`.
- **Small (S)**: Bounded strictly to `tests/test_blackbox_spell_vfx/`; all modules < 150 lines.
- **Testable (T)**: Frontdoor verification through pytest test suite execution against public endpoints and WebSockets.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `test_blackbox_spell_vfx.py` replaced by decomposed submodules under `tests/test_blackbox_spell_vfx/`.
   - All extracted test files strictly < 150 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest tests/test_blackbox_spell_vfx/`.
3. **Quality Gates**:
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
