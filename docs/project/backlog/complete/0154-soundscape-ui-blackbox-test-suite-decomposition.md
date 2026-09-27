---
id: '0154'
title: Soundscape UI Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0095
- TASK-0109
governing_adrs:
- ADR-0003
- ADR-0008
- ADR-0010
governing_prds:
- PRD-0010
governing_stories:
- US-0039
- US-0053
target_release: 0.5.0
pr_url: https://github.com/tyevans/runefoble/pull/176
---
# TASK-0154: Soundscape UI Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_soundscape_ui.py` (369 lines, 73.8% of limit) into modular test modules under `tests/test_blackbox_soundscape_ui/` (`test_manifest.py`, `test_stem_mixing.py`, `test_foley_ducking.py`, `conftest.py`), keeping all test files < 150 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_soundscape_ui.py` tests microfrontend manifests, tension-driven stem crossfades, WebAudio -12dB audio ducking, and DM foley soundboard triggers in a single 369-line file. Decomposing it into domain-focused test files improves test isolation and prevents file length violations.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structuring.
- **ADR-0008: Property and Mutation Testing with Hypothesis**: Clean test fixtures and parameterized test inputs.
- **ADR-0010: Continuous Integration Pipeline**: Parallelized test discovery in CI.

## Product & User Story References
- **Product Requirement**: [`prd-0010-adaptive-soundscape-foley-and-tension-scoring.md`](../../product/accepted/prd-0010-adaptive-soundscape-foley-and-tension-scoring.md)
- **User Story**: [`us-0039-encounter-tension-adaptive-scoring-and-foley.md`](../../user_stories/accepted/us-0039-encounter-tension-adaptive-scoring-and-foley.md)
- **User Story**: [`us-0053-dm-manual-soundboard-and-foley-triggers.md`](../../user_stories/accepted/us-0053-dm-manual-soundboard-and-foley-triggers.md)

## Detailed Specification & Implementation Plan
1. **Shared Fixtures (`tests/test_blackbox_soundscape_ui/conftest.py`)**:
   - Extract soundscape test client, audio state presets, and mock stems (< 90 lines).
2. **Manifest & Component Delivery Tests (`tests/test_blackbox_soundscape_ui/test_manifest.py`)**:
   - Verify `GET /ui/manifest`, Storybook asset bundle availability, and custom element tag registration (< 110 lines).
3. **Adaptive Stem Mixing Tests (`tests/test_blackbox_soundscape_ui/test_stem_mixing.py`)**:
   - Verify tension slider adjustments, ambient crossfade events, and track volume normalization (< 130 lines).
4. **Foley & Ducking Tests (`tests/test_blackbox_soundscape_ui/test_foley_ducking.py`)**:
   - Verify DM soundboard manual triggers, -12dB WebAudio ducking events, and voice priority override (< 120 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Test reorganization with zero production code changes.
- **Negotiable (N)**: Split of test scenarios across files can vary.
- **Valuable (V)**: Protects against file size violations and improves test execution clarity.
- **Estimable (E)**: Standard pytest test suite modularization.
- **Small (S)**: Bounded strictly to `tests/test_blackbox_soundscape_ui/`; all files < 150 lines.
- **Testable (T)**: Validated by 100% pass rate in `uv run pytest tests/test_blackbox_soundscape_ui/`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Test Architecture**:
   - `tests/test_blackbox_soundscape_ui/` created with focused test modules.
   - All test files strictly < 180 lines.
2. **Test Verification**:
   - All tests run and pass via `uv run pytest tests/test_blackbox_soundscape_ui/`.
3. **Quality Gates**:
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
