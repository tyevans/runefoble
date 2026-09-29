---
id: '0498'
title: Remove Backward Compatibility Shims & Re-exports in soundscape
status: Refined
created: 2026-09-29
dependencies:
- TASK-0230
- TASK-0436
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0010
governing_stories:
- US-0039
- US-0053
target_release: 0.9.0
---

# TASK-0498: Remove Backward Compatibility Shims & Re-exports in soundscape

## Status
Refined

## Summary
Purge transitional cue trigger wrappers, deprecated tension calculation shims, and package-root re-exports from `services/soundscape`, ensuring all internal and cross-service audio consumers interface strictly through canonical aggregate methods and event subscribers.

## Problem Statement
During the extraction of soundscape aggregate handlers (`TASK-0230`) and Gateway soundscape routing (`TASK-0436`), transitional method wrappers and legacy tension calculation shims were preserved in `soundscape/dependencies.py` and `soundscape/mixer.py` for backward compatibility. In accordance with the updated DoR, these transitional shims must be cleaned up, ensuring a single authoritative audio pipeline.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/manage-dynamic-soundscapes-and-audio-ducking.md`: Encounter tension and foley audio cues.
  - `docs/reference/ports-and-endpoints.md`: Soundscape service port 8010.
- **Governing Architecture & ADRs**:
  - **ADR-0006: Redis Streams Event Bus**: Audio mutation event publishing.
  - **ADR-0010: Real-Time Audio Pipeline and Ducking Coordination**: Soundscape controls and ducking coordination.
  - **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend component vendoring.

## Product & User Story References
- [`prd-0010-adaptive-soundscape-foley-and-tension-scoring.md`](../../product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md)
- [`us-0039-encounter-tension-adaptive-scoring-and-foley.md`](../../user_stories/accepted/us-0039-encounter-tension-adaptive-scoring-and-foley.md)
- [`us-0053-dm-manual-soundboard-and-foley-triggers.md`](../../user_stories/accepted/us-0053-dm-manual-soundboard-and-foley-triggers.md)

## Detailed Specification & Implementation Plan
1. **Remove Transitional Audio Cue Shims**:
   - In `services/soundscape/src/soundscape/dependencies.py` and `soundscape/mixer.py`, remove legacy cue trigger functions that wrap the underlying aggregate or event bus.
   - Ensure all callers invoke canonical `SoundscapeAggregate` methods or publish domain events directly.
2. **Remove Deprecated Tension Calculation Aliases**:
   - In `services/soundscape/src/soundscape/tension.py`, remove legacy tension formula shims, standardizing on the unified combat CR/round tension calculation engine.
3. **Clean Up `soundscape/__init__.py`**:
   - Prune package root re-exports to expose only authoritative service classes.
4. **Update Blackbox Test Suites**:
   - Verify tests in `tests/test_soundscape*` and `tests/test_blackbox_soundscape*` interact directly with canonical interfaces.

## INVEST Criteria Evaluation
- **Independent (I)**: Isolated cleanly to `services/soundscape`.
- **Negotiable (N)**: Clean standard Python method interfaces.
- **Valuable (V)**: Eliminates duplicate audio trigger code and unifies tension scoring.
- **Estimable (E)**: Scoped to `mixer.py`, `dependencies.py`, and `tension.py`.
- **Small (S)**: File changes well under 60 lines.
- **Testable (T)**: Verified via `uv run pytest tests/test_soundscape*`.

## Definition of Done
1. Transitional audio cue wrappers in `mixer.py` and `dependencies.py` removed.
2. Legacy tension formula shims removed in favor of canonical tension pipeline.
3. All callers and tests migrated to canonical interfaces.
4. All soundscape tests pass with zero warnings.
