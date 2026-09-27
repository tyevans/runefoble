---
id: '0177'
title: Runefoble Events Aggregator Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds: []
governing_stories: []
target_release: 0.7.0
---

# TASK-0177: Runefoble Events Aggregator Modular Decomposition

## Status
Proposed

## Summary
Decompose `libs/runefoble_events/src/runefoble_events/events.py` (420 lines, 84% of limit) and modularize domain event re-exports into focused category modules, ensuring all modules remain strictly < 200 lines per Hard Invariant 6.

## Problem Statement
`libs/runefoble_events/src/runefoble_events/events.py` has expanded to 420 lines as domain events from across the platform are imported and re-exported in a monolithic `__all__` list. With new domain events being introduced for West Marches, neural voice duplex, and 3D physics, this file will imminently breach the 500-line hard invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular package layout for core platform libraries.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for event definitions across bounded contexts.

## Scope of Work
1. **Domain Event Submodule Splitting (`libs/runefoble_events/src/runefoble_events/events/`)**:
   - Organize re-exports by domain family: `session_events.py`, `board_events.py`, `narrative_events.py`, and `world_events.py` (< 120 lines each).
2. **Aggregator Facade (`libs/runefoble_events/src/runefoble_events/events.py`)**:
   - Maintain backwards-compatible exports while reducing file length to < 100 lines.
3. **Verification**:
   - Ensure all existing event imports throughout the workspace continue to resolve without breaking changes.
   - Verify `uv run pytest` passes cleanly across all test suites.

## Definition of Done
- `events.py` reduced from 420 lines to < 100 lines.
- No single file in `libs/runefoble_events/` exceeds 200 lines.
- All workspace tests pass via `uv run pytest`.
- Linting and formatting pass via `uv run ruff check .` and `uv run ruff format --check .`.
