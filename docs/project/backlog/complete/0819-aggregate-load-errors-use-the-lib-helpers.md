---
id: '0819'
title: "Aggregate Load and Not-Found Handling Use the Lib Helpers"
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: runefoble_platform
target_release: 0.9.0
---

# TASK-0819: Aggregate Load and Not-Found Handling Use the Lib Helpers

## Status
Complete

## Summary
22 inline `except AggregateNotFoundError` blocks repeat what lib helpers already do, and repository accessors are hand-written get/set pairs.

## Problem Statement
- Findings SVC-07, SVC-08 in `.audit/research/services-backend.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0011.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Use the lib load helper (404 on missing) at every site.
2. Replace hand-written repository get/set pairs with the shared provider seam pattern (TASK-0773).

## Frontdoor Blackbox Test Plan
- Each changed route answers 404 for a missing aggregate, unchanged.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/services-backend.md` (SVC-07, SVC-08)
