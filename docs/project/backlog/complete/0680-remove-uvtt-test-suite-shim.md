---
id: '0680'
title: Remove the UVTT Blackbox Test Suite Re-export Shim
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0003
- ADR-0014
governing_prds:
- PRD-0022
governing_stories:
- US-0033
target_release: 0.9.0
severity: low
source_audits:
- work/0627.md
- work/0562.md
---

# TASK-0680: Remove the UVTT Blackbox Test Suite Re-export Shim

## Status
Complete

## Summary
`tests/test_blackbox_uvtt_import_suite.py` re-exports tests from the `tests/test_blackbox_uvtt_import/` package. Its docstring says "Maintains backward compatibility". DoR 9 forbids shims. This task deletes the shim and runs the tests from the package.

## Problem Statement
- `tests/test_blackbox_uvtt_import_suite.py` imports fixtures and tests from `tests.test_blackbox_uvtt_import.*` and lists them in `__all__`.
- No code in the repo imports this module (checked with grep on `*.py`, `*.toml`, `Makefile`).
- The basename clash noted in work/0562 no longer exists on main. Only the package directory and the shim remain.

## Documentation & Architecture Review
- AGENTS.md DoR 9: no shims or re-exports.
- ADR-0003: tests run through `uv run pytest`. Use the package path.
- ADR-0014: the blackbox tests stay in the package.

## Product & User Story References
- US-0033 (UVTT map importer): the test coverage stays the same. Only the entry point changes.

## Detailed Specification & Implementation Plan
1. Record the test count from `uv run pytest tests/test_blackbox_uvtt_import --collect-only -q`.
2. Delete `tests/test_blackbox_uvtt_import_suite.py`.
3. Check `docs/` and `docs/project/` for a live (not historical) reference to the shim path. Update live references only. Do not edit `complete/` backlog records.
4. Re-run collection. The count must match step 1.

## Frontdoor Blackbox Test Plan
- The test suite is the frontdoor. Run `uv run pytest tests/test_blackbox_uvtt_import` and `uv run pytest tests/test_blackbox_uvtt_doors_lights`. Both pass with the same test count as before.

## Definition of Done
- The shim file is deleted. `grep -rn "backward compatibility" tests/test_blackbox_uvtt_import_suite.py` finds nothing because the file is gone.
- Test counts match. `make lint` passes.
