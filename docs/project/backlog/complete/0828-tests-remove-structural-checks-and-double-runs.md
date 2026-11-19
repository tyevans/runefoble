---
id: '0828'
title: "Tests Remove Structural Checks, Facade Tests and Double-Run Bridges"
status: Complete
created: 2026-11-18
dependencies:
- TASK-0815
governing_adrs:
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: tests
target_release: 0.9.0
---

# TASK-0828: Tests Remove Structural Checks, Facade Tests and Double-Run Bridges

## Status
Complete

## Summary
Source-text and file-existence asserts remain (TASK-0681 forbids them), three bridge modules make tests run twice, and facade tests lock in shims.

## Problem Statement
- Findings T-03, T-22, T-23, T-24, T-25 in `.audit/research/tests.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0014.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Delete the structural asserts; keep any behaviour check. Delete the three bridge modules, `tests/helpers/app_shell_source.py` and the stale `collect_ignore` entry. Rewrite or delete facade tests.

4. Frontend node tests also hold line-count and file-existence blocks ("File Length Invariants"). Remove them from `frontend/test/stand-in-guardrails-decomposition.test.ts`, `bulletin-board-styles-decomposition.test.ts`, `radial-menu-decomposition.test.ts`, `character-sheet-actions-decomposition.test.ts`, `character-roster-styles-decomposition.test.ts` and `campaign-atlas-templates.test.ts`. Keep behaviour checks.

## Frontdoor Blackbox Test Plan
- The suite passes; the collected test count drops by the double-run tests.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/tests.md` (T-03, T-22, T-23, T-24, T-25)
