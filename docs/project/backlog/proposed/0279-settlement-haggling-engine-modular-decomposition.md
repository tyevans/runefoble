---
id: '0279'
title: Settlement Haggling Engine Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0262
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0024
governing_stories:
- US-0075
target_release: 0.8.0
---

# TASK-0279: Settlement Haggling Engine Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/src/game_session/settlement/haggling.py` (356 lines, 71.2% of limit) into modular domain submodules under `services/game_session/src/game_session/settlement/haggling/` (`state.py`, `rhetoric.py`, `dm_controls.py`), ensuring all haggling modules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/settlement/haggling.py` implements the interactive merchant negotiation state machine, rhetoric move resolution (flattery, intimidation, bundling, sob story), merchant patience and temperament adjustments, and live DM arbitration veto/accept controls in a single 356-line file. As new merchant personality quirks and multi-item trade bundle mechanics are added, this file will breach the 500-line invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module structuring within bounded contexts.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Real-time haggling state event emissions.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation.

## Scope of Work
1. **Haggling Session State Machine (`services/game_session/src/game_session/settlement/haggling/state.py`)**:
   - Extract session models, bargain states, price ranges, and patience counters (< 110 lines).
2. **Rhetoric Moves & Temperament Modifiers (`services/game_session/src/game_session/settlement/haggling/rhetoric.py`)**:
   - Extract player bartering moves, skill check formulas, merchant reaction formulas, and patience decay (< 120 lines).
3. **DM Arbitration & Veto Handlers (`services/game_session/src/game_session/settlement/haggling/dm_controls.py`)**:
   - Extract DM intervention endpoints, manual price overrides, dialogue injections, and deal approval/rejection (< 110 lines).
4. **Aggregator Facade (`services/game_session/src/game_session/settlement/haggling.py`)**:
   - Maintain re-export facade with full backwards compatibility (< 35 lines).
5. **Verification**:
   - Run haggling tests to confirm state machine and DM control integrity.

## Definition of Done
- `services/game_session/src/game_session/settlement/haggling.py` reduced to strictly < 40 lines.
- Extracted submodules under `haggling/` strictly < 130 lines each.
- Passes all haggling blackbox tests.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
