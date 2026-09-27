---
id: '0231'
title: Board Domain Events Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0004
- TASK-0007
- TASK-0019
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0007
- PRD-0013
governing_stories:
- US-0014
- US-0043
target_release: 0.8.0
---

# TASK-0231: Board Domain Events Modular Decomposition

## Status
Proposed

## Summary
Decompose `libs/runefoble_events/src/runefoble_events/board.py` (313 lines, 62.6% of limit) into focused event domain submodules under `libs/runefoble_events/src/runefoble_events/board_events/` (`token.py`, `fog.py`, `templates.py`, `lighting.py`), ensuring all domain event definition modules remain strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`libs/runefoble_events/src/runefoble_events/board.py` defines CloudEvents-compliant domain events for tactical token movement, fog-of-war visibility reveals, elevation changes, rotatable AoE templates, and dynamic point lights in a single 313-line file. As new 3D collision impulses and terrain destruction events are added, this file will breach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module boundaries across shared libraries.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: CloudEvents schema integrity and stream topics.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain event categorization.

## Scope of Work
1. **Token Events (`libs/runefoble_events/src/runefoble_events/board_events/token.py`)**:
   - Extract `TokenMoved`, `TokenKnockbackApplied`, and `ElevationChanged` (< 100 lines).
2. **Fog of War Events (`libs/runefoble_events/src/runefoble_events/board_events/fog.py`)**:
   - Extract `FogRevealed`, `ShroudReset`, and `VisibilityMaskUpdated` (< 80 lines).
3. **Template & Lighting Events (`libs/runefoble_events/src/runefoble_events/board_events/templates.py` & `lighting.py`)**:
   - Extract AoE spell template and dynamic lighting events (< 80 lines each).
4. **Aggregator Facade (`libs/runefoble_events/src/runefoble_events/board.py`)**:
   - Re-export all events maintaining full backwards compatibility (< 40 lines).
5. **Verification**:
   - Verify all board-related test suites pass cleanly.

## Definition of Done
- `board.py` reduced to strictly < 50 lines.
- Extracted submodules under `board_events/` strictly < 120 lines each.
- Passes `uv run pytest tests/test_blackbox_tactile_board.py`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
