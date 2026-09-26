---
id: 0095
title: Soundscape Blackbox Test Suite and Adaptive Mixer Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0050
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0009
- ADR-0013
target_release: 0.3.0
pr_url: https://github.com/tyevans/runefoble/pull/82
---
# TASK-0095: Soundscape Blackbox Test Suite and Adaptive Mixer Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_soundscape.py` (406 lines, 81.2% of limit) into two specialized blackbox test suites (`tests/test_blackbox_soundscape_transitions.py` and `tests/test_blackbox_soundscape_tension.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as spatial foley and leitmotif stems land.

## Problem Statement
`tests/test_blackbox_soundscape.py` spans 406 lines and bundles multiple distinct test concerns into a single file:
1. Audio stem mixing & ducking: Ambient background track crossfading, WebAudio -12dB voice ducking coordination upon `PlayerSpokeEvent`, and manual override controls.
2. Dynamic tension & combat reactivity: Threat score calculation, dynamic tension transitions upon `CombatEncounterStarted` and `CombatRoundAdvanced`, and tactical foley cue triggers (`SoundscapeCueTriggered`).
3. Zanzibar authorization: Permission enforcement for audio mixer adjustments and DM override controls.

As upcoming Milestone 5 features introduce Character Musical Leitmotifs (TASK-0102) and Audience Sound Effects (TASK-0051), this suite will exceed the 500-line limit without proactive partitioning.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python Bounded Contexts**: Preserves monorepo package layout.
- **ADR-0007: Real-Time Voice and Board Synchronization**: Dynamic ducking and audio pipeline synchronization.
- **ADR-0009: Continuous Backlog Refinement and Technical Debt Management**: Preemptive modularization.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: UI manifest and audio component integration.

## Proposed Decomposition
1. **Transitions & Ducking Blackbox Suite (`tests/test_blackbox_soundscape_transitions.py`)**:
   - Track crossfading, manual track changes, volume sliders, and WebAudio -12dB ducking toggle verification (< 210 lines).
2. **Combat Tension & Foley Blackbox Suite (`tests/test_blackbox_soundscape_tension.py`)**:
   - Dynamic tension score calculation, combat event listeners (`CombatStarted`, `CombatRoundAdvanced`), tactical foley cue triggers, and Zanzibar DM permissions (< 210 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors test structure without altering `services/soundscape` HTTP endpoints, audio state, or CloudEvent schemas.
- **Negotiable (N)**: Allocation of Zanzibar permission tests between suites can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and speeds up test suite execution.
- **Estimable (E)**: Clean pytest module separation with shared fixtures.
- **Small (S)**: Scope strictly isolated to `tests/test_blackbox_soundscape.py`; all files < 220 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_blackbox_soundscape_*.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Test Suites**:
   - `tests/test_blackbox_soundscape_transitions.py` and `tests/test_blackbox_soundscape_tension.py` created with frontdoor setup.
   - All test files strictly under 220 lines.
2. **Full Scenario Coverage**:
   - 100% test pass rate across all 12 existing soundscape test scenarios.
3. **Strict Invariant Adherence**:
   - Conforms to Hard Invariant 6 (< 500 lines) and Hard Invariant 7 (public HTTP frontdoors and CloudEvents).
4. **Quality Gates**:
   - Passes `uv run ruff check` and `uv run ruff format --check`.
