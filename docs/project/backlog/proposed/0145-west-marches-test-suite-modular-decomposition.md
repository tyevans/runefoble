---
id: '0145'
title: West Marches Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0127
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0011
target_release: 0.5.0
---

# TASK-0145: West Marches Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_west_marches.py` (402 lines, approaching limit) into specialized test modules (`test_west_marches_discovery.py`, `test_west_marches_caravan.py`, `test_west_marches_security.py`) to keep all test files comfortably below 200 lines per Hard Invariant 6.

## Problem Statement
Following the merge of TASK-0127, `tests/test_blackbox_west_marches.py` contains 402 lines covering multi-party discovery synchronization, scheduled caravan transit, and SpiceDB Zanzibar multi-tenancy access control. Proactively decomposing it safeguards against breaching Hard Invariant 6 (< 500 lines).

## Governing Architecture & ADRs
- **ADR-0001**: SpiceDB Zanzibar access control testing.
- **ADR-0006**: Redis Streams event testing.
- **ADR-0011**: eventsource-py aggregate reload testing.

## Scope of Work
1. **Discovery Synchronization Tests (`tests/test_blackbox_west_marches/test_discovery.py`)**:
   - Extract multi-party waypoint sharing and expedition milestone tests (< 140 lines).
2. **Caravan Trade Tests (`tests/test_blackbox_west_marches/test_caravan.py`)**:
   - Extract ledger updates and settlement shop unlocking tests (< 140 lines).
3. **Security & Zanzibar Isolation Tests (`tests/test_blackbox_west_marches/test_security.py`)**:
   - Extract multi-tenancy boundary and unshared secrets tests (< 140 lines).
4. **Verification**:
   - Run pytest and confirm 100% test pass rate.
