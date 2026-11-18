---
id: '0790'
title: Test Helpers Wait Without Spinning, Report Failed Cleanup, and Read Public State
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: tests
target_release: 0.9.0
---

# TASK-0790: Test Helpers Wait Without Spinning, Report Failed Cleanup, and Read Public State

## Status
Complete

## Summary
Three test hygiene defects: a busy wait, silent cleanup failure, and a physics test that reads private store state.

## Problem Statement
- `tests/helpers/redis_container.py` (`_wait_for_redis`): no sleep when `ping()` returns False.
- `tests/helpers/postgres.py` and `tests/helpers/redis_container.py`: teardown ignores the `docker rm -f` return code.
- `tests/test_blackbox_tabletop_physics.py:98-148`: reads `store._events` for `DiceSettled` and `PhysicsCollisionOccurred` (Hard Invariant 7).

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0014.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Sleep between readiness probes.
2. Report a failed removal as a teardown error with the container name.
3. Assert through the public board read model or the published events on the mock bus.

## Frontdoor Blackbox Test Plan
- The physics test passes with no private store attribute.
- A failed removal shows in the test output.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `.audit/work/0781.md`, `.audit/work/0782.md` (Discovered)
