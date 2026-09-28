---
id: '0292'
title: Tavern and Haggling Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0103
- TASK-0262
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0006
- ADR-0013
governing_prds:
- PRD-0014
- PRD-0024
governing_stories:
- US-0047
- US-0075
target_release: 0.8.0
---

# TASK-0292: Tavern and Haggling Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_tavern_and_haggling.py` (296 lines, 59.2% of limit) into modular test submodules under `tests/test_blackbox_tavern_and_haggling/` (`conftest.py`, `test_tavern_parlor.py`, `test_liars_dice.py`, `test_drinking_contest.py`, `test_haggling_integration.py`), ensuring all test files remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_tavern_and_haggling.py` covers frontdoor blackbox verification for tavern minigames, Liar's Dice wagering, drinking contests with DSP vocal filters, and merchant haggling integration. As additional casino minigames (TASK-0261) and DM arbitration workflows expand the social mechanics, this monolithic test file will approach the 500-line invariant limit unless modularized into focused test suites.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Authorization checks for tavern games and haggling sessions.
- **ADR-0002: Domain Events via eventsource-py**: Verification of emitted domain events.
- **ADR-0006: Redis Streams Event Bus**: Event stream publishing verification.
- **ADR-0013: Modular Decomposition**: All files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_tavern_and_haggling/conftest.py`)**:
   - Extract mock Redis event bus, FastAPI test clients, and SpiceDB mock fixtures (< 60 lines).
2. **Tavern Parlor Manifest & UI Tests (`tests/test_blackbox_tavern_and_haggling/test_tavern_parlor.py`)**:
   - Extract microfrontend manifest checks, component availability, and parlor static assets (< 70 lines).
3. **Liar's Dice Wagering Tests (`tests/test_blackbox_tavern_and_haggling/test_liars_dice.py`)**:
   - Extract dice bidding, challenge resolution, bluff verification, and gold purse transfers (< 100 lines).
4. **Drinking Contest Tests (`tests/test_blackbox_tavern_and_haggling/test_drinking_contest.py`)**:
   - Extract constitution saving throws, intoxication stages, DSP slurred speech filters, and blackout events (< 90 lines).
5. **Haggling Integration Tests (`tests/test_blackbox_tavern_and_haggling/test_haggling_integration.py`)**:
   - Extract merchant negotiation start, posture evaluation, and barter transaction events (< 100 lines).
6. **Verification**:
   - Safely remove monolithic `tests/test_blackbox_tavern_and_haggling.py` and run `uv run pytest tests/test_blackbox_tavern_and_haggling/`.

## Definition of Done
- `tests/test_blackbox_tavern_and_haggling.py` decomposed into `tests/test_blackbox_tavern_and_haggling/` suite.
- All extracted test files strictly < 110 lines per Hard Invariant 6.
- 100% test passing via `uv run pytest tests/test_blackbox_tavern_and_haggling/`.
- Monolithic `tests/test_blackbox_tavern_and_haggling.py` safely removed.
