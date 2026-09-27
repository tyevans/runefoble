---
id: '0233'
title: Character Leitmotif Generator Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0050
- TASK-0102
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds:
- PRD-0016
governing_stories:
- US-0046
target_release: 0.8.0
---

# TASK-0233: Character Leitmotif Generator Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/soundscape/src/soundscape/leitmotif.py` (315 lines, 63.0% of limit) into modular submodules under `services/soundscape/src/soundscape/leitmotif/` (`chords.py`, `instruments.py`, `generator.py`), ensuring all modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/soundscape/src/soundscape/leitmotif.py` handles harmonic scale generation, character archetype instrumentation synthesis, and melodic contour generation in a single 315-line file. As new orchestral instrumentation maps and villain motifs are added, this file will approach the 500-line ceiling unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module boundaries within bounded contexts.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain entity segregation.

## Scope of Work
1. **Chord Scales (`services/soundscape/src/soundscape/leitmotif/chords.py`)**:
   - Extract chord scales, harmonic progressions, and tension pitch shifts (< 110 lines).
2. **Instrumentation (`services/soundscape/src/soundscape/leitmotif/instruments.py`)**:
   - Extract timbre definitions, character class instrument mappings, and mood presets (< 110 lines).
3. **Leitmotif Generator (`services/soundscape/src/soundscape/leitmotif/generator.py`)**:
   - Extract core leitmotif assembly and melody generation (< 110 lines).
4. **Aggregator Facade (`services/soundscape/src/soundscape/leitmotif.py`)**:
   - Re-export `LeitmotifGenerator` maintaining full backwards compatibility (< 30 lines).
5. **Verification**:
   - Verify soundscape tests pass with `uv run pytest services/soundscape/`.

## Definition of Done
- `leitmotif.py` reduced to strictly < 40 lines.
- Extracted submodules under `leitmotif/` strictly < 130 lines each.
- Passes `uv run pytest services/soundscape/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
