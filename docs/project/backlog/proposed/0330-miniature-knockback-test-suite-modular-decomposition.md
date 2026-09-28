---
id: '0330'
title: Miniature Knockback Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0171
governing_adrs:
- ADR-0006
- ADR-0011
- ADR-0013
governing_prds:
- PRD-0021
governing_stories:
- US-0061
target_release: 0.8.0
---

# TASK-0330: Miniature Knockback Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_miniature_knockback/test_knockback_impulse_and_elevation.py` (273 lines, 54.6% of limit) into modular sub-suites under `tests/test_blackbox_miniature_knockback/` (`test_knockback_linear_impulse.py`, `test_knockback_elevation_barriers.py`, and `test_knockback_restitution.py`) with shared frontdoor fixtures, keeping all test files strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_miniature_knockback/test_knockback_impulse_and_elevation.py` tests multiple disparate physical aspects of tabletop miniature physics: linear knockback impulse calculations, elevation cliff barriers, collision event emission, and boundary bounce restitutions in a single test module. As additional physics models (e.g., tumbling, friction, rolling momentum) are added, this file will exceed the 500-line invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Verification of `PhysicsCollisionOccurred` and `TokenMoved` events.
- **ADR-0011: eventsource-py Core Event Sourcing**: Event-sourced state assertions.
- **ADR-0013: Modular Decomposition**: All source and test files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Shared Knockback Fixtures (`tests/test_blackbox_miniature_knockback/fixtures.py`)**:
   - Extract `_create_board`, `_place_token`, and `_set_terrain_elevation` helper routines (< 60 lines).
2. **Linear Impulse Suite (`tests/test_blackbox_miniature_knockback/test_knockback_linear_impulse.py`)**:
   - Extract standard knockback vector tests, boundary clamping, and friendly/enemy token push physics (< 100 lines).
3. **Elevation Barrier Suite (`tests/test_blackbox_miniature_knockback/test_knockback_elevation_barriers.py`)**:
   - Extract cliff edge detection, elevation difference thresholds, and fall damage triggers (< 90 lines).
4. **Collision & Restitution Suite (`tests/test_blackbox_miniature_knockback/test_knockback_restitution.py`)**:
   - Extract wall bounce restitution, token-to-token physical collisions, and event payload verification (< 95 lines).
5. **Aggregator Entry Point (`tests/test_blackbox_miniature_knockback/test_knockback_impulse_and_elevation.py`)**:
   - Re-export test cases to preserve pytest discovery compatibility (< 30 lines).

## Definition of Done
- `test_knockback_impulse_and_elevation.py` decomposed into focused sub-suites with shared fixtures.
- All test files strictly < 110 lines each per Hard Invariant 6.
- `pytest tests/test_blackbox_miniature_knockback/` passes with 100% success rate.
