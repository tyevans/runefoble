---
id: '0130'
title: Character Leitmotifs Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0102
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0006
- ADR-0009
- ADR-0010
- ADR-0013
target_release: 0.4.0
governing_prds:
- PRD-0016
governing_stories:
- US-0046
pr_url: https://github.com/tyevans/runefoble/pull/140
---
# TASK-0130: Character Leitmotifs Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose monolithic `tests/test_blackbox_character_leitmotifs.py` (437 lines, 87.4% of limit) into discrete, single-responsibility blackbox test modules (`tests/test_blackbox_leitmotif_events.py`, `tests/test_blackbox_leitmotif_api.py`, and `tests/test_blackbox_leitmotif_triggers.py`), keeping all resulting test files strictly under 200 lines and maintaining 100% test coverage.

## Problem Statement
`tests/test_blackbox_character_leitmotifs.py` currently spans 437 lines, approaching the 500-line hard invariant limit (Hard Invariant 6). It consolidates multiple test domains in a single file:
1. CloudEvents schema registration and event mapping for `runefoble.events.soundscape.leitmotif_*` and `runefoble.events.character.*`.
2. REST API route testing for leitmotif profile configuration, playback triggers, and SpiceDB Zanzibar access control.
3. Multi-modal event triggers (critical hits, death saves, spoken reactions) and WebAudio DSP ducking gain calculations.

As additional character audio signatures and DSP filters are added, this file is at immediate risk of breaching Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Architecture & Voice Audio**: Low-latency DSP ducking and voice envelope coordination.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular separation of test suites within the monorepo.
- **ADR-0006: Redis Streams Event Bus**: CloudEvents domain event schemas and subscription testing.
- **ADR-0009: Code Quality and Linting with Ruff and Pre-commit**: Modular test boundaries and single-responsibility modules.
- **ADR-0010: OpenTelemetry Distributed Tracing**: Trace context propagation in audio triggers.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Client audio playback and stem mixing boundaries.

## Product & User Story References
- **Product Requirement**: [`prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md`](../../product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md)
- **User Story**: [`us-0046-character-musical-leitmotifs-and-dynamic-themes.md`](../../user_stories/accepted/us-0046-character-musical-leitmotifs-and-dynamic-themes.md)

## Detailed Specification & Implementation Plan
1. **CloudEvents Registration Suite (`tests/test_blackbox_leitmotif_events.py`)**:
   - Tests validating CloudEvents event class mapping (`LeitmotifProfileConfigured`, `LeitmotifTriggered`, `CriticalHitScored`, `DeathSaveStarted`).
   - Serialization and deserialization verification for audio theme metadata and volume multipliers (< 120 lines).
2. **REST API & Zanzibar Auth Suite (`tests/test_blackbox_leitmotif_api.py`)**:
   - Tests exercising `/api/v1/soundscape/leitmotif/profile` and `/api/v1/soundscape/leitmotif/trigger`.
   - SpiceDB Zanzibar authorization checks ensuring only character owners and DMs can configure audio signatures (< 160 lines).
3. **Domain Event Triggers & DSP Ducking Suite (`tests/test_blackbox_leitmotif_triggers.py`)**:
   - Tests verifying event bus reaction handlers for critical hits, death saves, and spoken reactions.
   - Validation of `calculate_envelope_gain` mathematical attenuation formulas and ducking constants (< 180 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Pure test suite refactoring without modifying soundscape engine business logic or domain schemas.
- **Negotiable (N)**: Split boundaries between event triggers and ducking gain tests can be adjusted.
- **Valuable (V)**: Protects codebase health against invariant breaches and improves test execution parallelism.
- **Estimable (E)**: Direct decomposition of existing pytest test cases.
- **Small (S)**: Scope strictly isolated to `tests/`; all resulting files < 200 lines.
- **Testable (T)**: Verified by running `uv run pytest tests/test_blackbox_leitmotif_*.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Decomposed Test Modules**:
   - `tests/test_blackbox_character_leitmotifs.py` eliminated; replacement test files each strictly < 200 lines.
2. **Zero Regressions**:
   - 100% of existing leitmotif assertions pass without modification.
3. **Quality Gates**:
   - Hard Invariant 6 met with zero files exceeding 500 lines.
   - Passes `uv run pytest tests/test_blackbox_leitmotif_*.py` and `uv run ruff check .`.
