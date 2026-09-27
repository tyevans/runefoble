---
id: '0177'
title: Runefoble Events Aggregator Modular Decomposition
status: Complete
created: 2026-09-26
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds: []
governing_stories: []
target_release: 0.7.0
pr_url: https://github.com/tyevans/runefoble/pull/228
---
# TASK-0177: Runefoble Events Aggregator Modular Decomposition

## Status
Refined

## Summary
Decompose `libs/runefoble_events/src/runefoble_events/events.py` (474 lines, 94.8% of limit) and `libs/runefoble_events/src/runefoble_events/__init__.py` (442 lines, 88.4% of limit), modularizing domain event re-exports into focused category modules, ensuring all modules remain strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`libs/runefoble_events/src/runefoble_events/events.py` has grown to 474 lines and `libs/runefoble_events/src/runefoble_events/__init__.py` has reached 442 lines as domain events from across the platform are imported and re-exported in monolithic `__all__` lists. With new domain events continually being introduced for West Marches, neural voice duplex, and 3D physics, these files will imminently breach the 500-line hard invariant unless decomposed into domain category submodules.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular package layout for core platform libraries.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for event definitions across bounded contexts.

## Detailed Specification & Implementation Plan
1. **Domain Event Submodule Splitting (`libs/runefoble_events/src/runefoble_events/events/`)**:
   - `session_events.py`: Turn, initiative, presence, and dice events (< 100 lines).
   - `board_events.py`: Spatial grid, token motion, fog-of-war, and terrain events (< 110 lines).
   - `narrative_events.py`: Watcher DM utterances, story recaps, and AI stand-in events (< 100 lines).
   - `world_events.py`: Faction agendas, trade caravans, haven settlements, and lore events (< 110 lines).
2. **Aggregator Facades (`events.py` & `__init__.py`)**:
   - Maintain 100% backwards-compatible exports while reducing file length of each aggregator facade to < 80 lines.
3. **Verification**:
   - Ensure all existing event imports throughout all services and libraries continue to resolve without breaking changes.
   - Run the complete workspace test suite via `uv run pytest` to verify zero import regressions.

## INVEST Criteria Evaluation
- **Independent (I)**: Structural decomposition with zero API breaking changes; does not block other service work.
- **Negotiable (N)**: Submodule category naming boundaries can be adjusted based on domain affinities.
- **Valuable (V)**: Protects core event definitions from breaching Hard Invariant 6 (500-line limit) and improves code navigation.
- **Estimable (E)**: Pure refactoring and re-export packaging with existing unit test coverage.
- **Small (S)**: Bounded strictly to `libs/runefoble_events/`; all modules < 150 lines.
- **Testable (T)**: Workspace-wide test suite execution validates backwards compatibility across all bounded contexts.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `events.py` and `__init__.py` reduced to strictly < 80 lines each.
   - All extracted submodules in `libs/runefoble_events/src/runefoble_events/` strictly < 150 lines per Hard Invariant 6.
2. **Backwards Compatibility & Verification**:
   - All public domain events re-exported identically from `runefoble_events`.
   - Full test suite passes via `uv run pytest`.
3. **Quality Gates**:
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
