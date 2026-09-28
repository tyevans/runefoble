---
id: '0326'
title: Game Session Tavern Router Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0103
- TASK-0292
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0006
- ADR-0013
governing_prds:
- PRD-0014
governing_stories:
- US-0047
target_release: 0.8.0
---

# TASK-0326: Game Session Tavern Router Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/src/game_session/routers/tavern.py` (273 lines, 54.6% of limit) into modular APIRouter submodules under `services/game_session/src/game_session/routers/tavern/` (`tavern_games_router.py`, `tavern_merchants_router.py`, and router aggregator), keeping each module strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/routers/tavern.py` combines minigame initiation/turn resolution (Liar's Dice, drinking contests) and merchant haggling dialogue into a single router file. As new tavern gambling games, cheating mechanics, and NPC dialogue models are integrated, this file will threaten the 500-line limit unless decomposed into dedicated sub-routers.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Relationship verification and player authorization.
- **ADR-0002: Domain Events via eventsource-py**: TavernGameAggregate and MerchantAggregate event sourcing.
- **ADR-0006: Redis Streams Transport**: Event bus publishing for tavern turns and haggling results.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 120 lines).

## Scope of Work
1. **Tavern Games Router (`services/game_session/src/game_session/routers/tavern/tavern_games_router.py`)**:
   - Endpoints for starting games, resolving turns (bids, challenges, drinks), and checking game state (< 110 lines).
2. **Merchant Haggling Router (`services/game_session/src/game_session/routers/tavern/tavern_merchants_router.py`)**:
   - Endpoints for initiating haggling rounds, evaluating counter-offers, and settling transactions (< 110 lines).
3. **Router Aggregator (`services/game_session/src/game_session/routers/tavern.py`)**:
   - Re-export composable APIRouter combining both sub-routers with backward compatibility (< 35 lines).
4. **Verification**:
   - Run blackbox tests (`tests/test_blackbox_tavern_and_haggling.py`) to verify 100% pass rate.

## Definition of Done
- `tavern.py` router decomposed into modular sub-routers.
- All extracted files strictly < 120 lines each per Hard Invariant 6.
- 100% test pass rate preserved across tavern minigame and haggling test suites.
