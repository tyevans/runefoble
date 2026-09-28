---
id: '0338'
title: Campaign Lore Handouts Generator Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0101
governing_adrs:
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0015
governing_stories:
- US-0045
target_release: 0.8.0
---

# TASK-0338: Campaign Lore Handouts Generator Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/campaign_lore/src/campaign_lore/handouts.py` (285 lines, 57.0% of limit) into modular Python submodules under `services/campaign_lore/src/campaign_lore/handouts/` (`constants.py`, `physics.py`, `relics.py`, `generator.py`), ensuring all modules remain strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`services/campaign_lore/src/campaign_lore/handouts.py` bundles wax seal SVG stamp definitions, seal color palettes, parchment texture presets, wax fracture acoustic physics, UV invisible ink revelation equations, and 3D relic GLTF mesh synthesis in a single 285-line file. As additional diegetic handout styles and 3D artifact shaders are introduced, this file will trend toward the 500-line ceiling unless modularized.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/inspect-diegetic-handouts-and-3d-relics.md`: Wax seals, parchment textures, invisible ink runes, and 3D WebGL relics.
  - `docs/reference/diegetic-handouts-and-relics-events.md`: CloudEvents schemas and payload structures for diegetic artifacts.
- **Governing Architecture & ADRs**:
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation in campaign lore.
  - **ADR-0013: Modular Decomposition**: Single-responsibility Python modules strictly < 150 lines.

## Scope of Work & Implementation Plan
1. **Parchment and Seal Constants (`services/campaign_lore/src/campaign_lore/handouts/constants.py`)**:
   - Extract `SEAL_STAMPS`, `SEAL_COLORS`, and `PAPER_TEXTURES` dictionaries (< 80 lines).
2. **Wax Seal Physics & Fracture (`services/campaign_lore/src/campaign_lore/handouts/physics.py`)**:
   - Extract seal break physics, acoustic resonance calculation, and fracture geometry (< 80 lines).
3. **3D Relic Synthesizer (`services/campaign_lore/src/campaign_lore/handouts/relics.py`)**:
   - Extract 3D WebGL relic mesh synthesis and UV ink revelation equations (< 80 lines).
4. **Handout Generator Engine (`services/campaign_lore/src/campaign_lore/handouts/generator.py`)**:
   - Extract `HandoutGenerator` assembling textures, seals, and ink layers (< 90 lines).
5. **Facade Re-export (`services/campaign_lore/src/campaign_lore/handouts.py`)**:
   - Re-export all classes, dictionaries, and helpers for backward compatibility (< 35 lines).
6. **Verification**:
   - Verify all tests pass via `uv run pytest tests/test_blackbox_diegetic_handouts_and_relics.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal service module decomposition preserving all public handout engine signatures.
- **Negotiable (N)**: Submodule grouping can be adjusted cleanly.
- **Valuable (V)**: Safeguards campaign lore artifact generation against violating Hard Invariant 6.
- **Estimable (E)**: Clean separation of dictionary constants, physical geometry, and mesh synthesis.
- **Small (S)**: Submodules will each be strictly < 100 lines.
- **Testable (T)**: Existing diegetic handouts blackbox test suite validates artifact output.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `services/campaign_lore/src/campaign_lore/handouts.py` reduced to a facade < 40 lines.
2. Modular submodules in `services/campaign_lore/src/campaign_lore/handouts/` strictly < 100 lines each.
3. Full backward compatibility maintained.
4. All diegetic handout tests pass via `uv run pytest tests/test_blackbox_diegetic_handouts_and_relics.py`.
5. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
