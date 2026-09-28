---
id: '0310'
title: Minigames Suite Blackbox Test Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0261
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0074
target_release: 0.8.0
---

# TASK-0310: Minigames Suite Blackbox Test Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_minigames_suite.py` (315 lines, 63% of limit) into modular test sub-modules under `tests/test_blackbox_minigames_suite/` (`conftest.py`, `test_manifest.py`, `test_liars_dice.py`, `test_drinking_contest.py`, `test_roulette.py`), keeping each test module strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_minigames_suite.py` validates the entire mobile-first tavern and casino minigames suite, including microfrontend manifest registration, Liar's Dice wagers/bids/challenges, Drinking Contest CON saves/intoxication DSP stages, and Roulette wheel spins/payout calculations in a single 315-line file. As new casino minigames (Craps, Dragon's Ante) and spectator betting are integrated, this file will rapidly exceed 500 lines unless decoupled into focused sub-suites.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test suite organization.
- **ADR-0007: Domain-Driven Design Architecture**: Blackbox domain verification.
- **ADR-0013: Modular Decomposition**: All test files kept strictly < 500 lines (submodules < 150 lines).

## Scope of Work
1. **Test Fixtures & Environment (`tests/test_blackbox_minigames_suite/conftest.py`)**:
   - Shared client fixtures, mock event bus, and SpiceDB client (< 60 lines).
2. **Manifest & Invariants (`tests/test_blackbox_minigames_suite/test_manifest.py`)**:
   - Manifest endpoints and file length invariant verification (< 60 lines).
3. **Liar's Dice & Drinking Sub-Suites (`tests/test_blackbox_minigames_suite/test_tavern_minigames.py`)**:
   - Bidding, challenges, intoxication progression, and audio DSP stages (< 120 lines).
4. **Roulette & Casino Sub-Suites (`tests/test_blackbox_minigames_suite/test_casino_minigames.py`)**:
   - Wheel bets, payouts, and multiplier calculations (< 120 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_minigames_suite/` to confirm all assertions pass.

## Definition of Done
- `tests/test_blackbox_minigames_suite.py` migrated to `tests/test_blackbox_minigames_suite/` package.
- All extracted test modules strictly < 150 lines each per Hard Invariant 6.
- 100% test coverage preserved with all existing test cases passing cleanly.
