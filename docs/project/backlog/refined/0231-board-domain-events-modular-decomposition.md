---
id: '0231'
title: Board Domain Events Modular Decomposition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0004
- TASK-0007
- TASK-0019
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0013
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
Refined

## Summary
Decompose `libs/runefoble_events/src/runefoble_events/board.py` (313 lines, 62.6% of limit) into focused event domain submodules under `libs/runefoble_events/src/runefoble_events/board_events/` (`token.py`, `fog.py`, `templates.py`, `lighting.py`), ensuring all domain event definition modules remain strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`libs/runefoble_events/src/runefoble_events/board.py` defines CloudEvents-compliant domain events for tactical token movement, fog-of-war visibility reveals, elevation changes, rotatable AoE templates, and dynamic point lights in a single 313-line file. As new 3D collision impulses and terrain destruction events are added, this file will breach the 500-line limit unless decomposed.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/reference/events-schema.md`: CloudEvents domain events catalogue and schema validation.
  - `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`: Token kinematics, distance measuring, and ghost previews.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module boundaries across shared libraries.
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: CloudEvents schema integrity and stream topics.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain event categorization.
  - **ADR-0013: Modular Decomposition**: Domain event submodules strictly < 150 lines.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
  - [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
  - [`us-0014-realtime-board-websocket-sync.md`](../../user_stories/accepted/us-0014-realtime-board-websocket-sync.md)
  - [`us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md`](../../user_stories/accepted/us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md)

## Detailed Specification & Implementation Plan
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

## INVEST Criteria Evaluation
- **Independent (I)**: Internal module organization without breaking event topic strings or payload schemas.
- **Negotiable (N)**: Submodule file boundaries can be tailored.
- **Valuable (V)**: Protects core board domain events from breaching the 500-line invariant limit.
- **Estimable (E)**: Event class extraction and re-export facade.
- **Small (S)**: Submodules will each be strictly < 120 lines.
- **Testable (T)**: Event serialization tests and board blackbox tests verify 100% compatibility.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `libs/runefoble_events/src/runefoble_events/board.py` reduced to strictly < 50 lines.
2. Extracted submodules under `board_events/` strictly < 120 lines each.
3. Passes `uv run pytest tests/test_blackbox_tactile_board.py` and `tests/test_board_events.py`.
4. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
