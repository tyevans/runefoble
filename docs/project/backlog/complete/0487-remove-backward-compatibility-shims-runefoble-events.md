---
id: '0487'
title: Remove Backward Compatibility Shims & Re-exports in runefoble_events
status: Complete
created: 2026-09-29
dependencies:
- TASK-0231
governing_adrs:
- ADR-0006
- ADR-0011
governing_prds:
- PRD-0001
governing_stories:
- US-0010
target_release: 0.9.0
---

# TASK-0487: Remove Backward Compatibility Shims & Re-exports in runefoble_events

## Status
Complete

Audit 2026-11-17: file list corrected. `soundscape_events.py` does not exist. Also remove the alias `TrapPlaced = TrapPlacedEvent` (`board_traps.py:93`). `events.py`, `board.py`, and the `board_events/` and `watcher_events/` directories are decided by TASK-0579 and are not deleted here.

## Summary
Delete all package-root backward-compatibility alias modules in `libs/runefoble_events` (`board_events.py`, `narrative_events.py`, `platform_events.py`, `world_events.py`, `media_events.py`, `session_events.py`, `character_events.py`), updating all domain callers to import directly from `runefoble_events.events.<category>`, and remove obsolete parity tests.

## Problem Statement
When domain events were modularized into `runefoble_events.events.*`, the root of `libs/runefoble_events/src/runefoble_events/` retained legacy alias files (`board_events.py`, `narrative_events.py`, `platform_events.py`, `world_events.py`, `media_events.py`, `session_events.py`, `character_events.py`) that merely re-export symbols for backward compatibility. Furthermore, tests like `tests/test_runefoble_events_modular_decomposition.py:test_backward_compatibility_re_export_parity` (removed) actively verify these shims. In accordance with the DoR zero backward compatibility mandate, these alias files must be deleted and all consumers migrated to authoritative paths.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/reference/events-schema.md`: CloudEvents domain event schemas and categories.
  - `docs/how-to/define-event-sourced-aggregates.md`: Authoritative event imports.
- **Governing Architecture & ADRs**:
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event serialization and cataloguing.
  - **ADR-0011: eventsource-py Core Event Sourcing**: Event registration and aggregate handlers.

## Product & User Story References
- [`prd-0001-runefoble-platform-foundations.md`](../../product/accepted/prd-0001-runefoble-platform-foundations.md)
- [`us-0010-developer-local-infrastructure-and-test-tooling.md`](../../user_stories/accepted/us-0010-developer-local-infrastructure-and-test-tooling.md)

## Detailed Specification & Implementation Plan
1. **Delete Root Alias Files in `libs/runefoble_events`**:
   - Delete `libs/runefoble_events/src/runefoble_events/events/board_events.py` (removed).
   - Delete `libs/runefoble_events/src/runefoble_events/events/narrative_events.py` (removed).
   - Delete `libs/runefoble_events/src/runefoble_events/events/platform_events.py` (removed).
   - Delete `libs/runefoble_events/src/runefoble_events/events/world_events.py` (removed).
   - Delete `libs/runefoble_events/src/runefoble_events/events/media_events.py` (removed), `session_events.py`, and `character_events.py` (each is an 8-line facade).
   - Delete the stray facade `libs/runefoble_events/src/runefoble_events/settlement_workers.py` (outside `src/`). Keep `src/runefoble_events/settlement_workers.py`: it is a 100-line module, not an alias.
2. **Update Package Root `__init__.py`**:
   - Clean up `libs/runefoble_events/src/runefoble_events/__init__.py` to re-export only canonical core base classes (`BaseRunefobleEvent`, `DomainEvent`, `register_event`), removing obsolete re-export facades.
3. **Migrate Import Sites Across All Services**:
   - Search the entire repository for imports from `runefoble_events.board_events`, `runefoble_events.narrative_events`, etc., and rewrite them to `runefoble_events.events.board_events`, `runefoble_events.events.narrative_events`, etc.
4. **Update Blackbox Test Suites**:
   - In `tests/test_runefoble_events_modular_decomposition.py`, remove `test_backward_compatibility_re_export_parity()` and update remaining tests to verify domain events exclusively through their canonical modular paths.

## INVEST Criteria Evaluation
- **Independent (I)**: Completely decouples `runefoble_events` structure from legacy root imports.
- **Negotiable (N)**: Direct import paths follow established Diataxis and ADR conventions.
- **Valuable (V)**: Eliminates the redundant shim files and prevents developer confusion on canonical import paths.
- **Estimable (E)**: A fixed list of facade files (see the Summary), root `__init__.py` to clean, and known test suite to prune.
- **Small (S)**: Straightforward file deletions and import migrations.
- **Testable (T)**: Verified by `uv run pytest tests/test_runefoble_events*.py` and cross-service test suites.

## Definition of Done
1. All root alias files listed in the Summary deleted.
2. Root `__init__.py` exposes only authoritative base event types.
3. All repository import sites migrated to `runefoble_events.events.*`.
4. Obsolete backward-compatibility parity tests removed.
5. All Python tests pass and `make lint` reports zero issues.

## Orchestrator Addenda (2026-11-17)

Source: `.audit/synth/discovered-round1.md`.

- Alias assignments `X = XEvent` remain in `aec.py`, `faction_resources.py`, `turf_war.py`, `settlements.py`, `board_traps.py`, `mcp_tools.py` (lines 61-63), `vocal_dsp.py`, `combat_reactions.py`, and `voice_barge_in.py`. Delete them and their `__all__` entries. `grep -rn '^[A-Za-z]* = [A-Za-z]*Event$' libs/runefoble_events/src` must return nothing.
