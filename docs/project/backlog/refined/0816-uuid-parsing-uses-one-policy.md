---
id: '0816'
title: "UUID Parsing Uses One Policy in Every Service"
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: runefoble_platform
target_release: 0.9.0
---

# TASK-0816: UUID Parsing Uses One Policy in Every Service

## Status
Refined

## Summary
About 28 UUID helpers use three policies: raise 400, return None, or substitute a random UUID.

## Problem Statement
- Findings SVC-04 in `.audit/research/services-backend.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0015.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Add one helper in `runefoble_platform` that turns bad input into a 422/400 error with the field name. Never substitute a value.
2. Replace every local helper. Prefer typed `UUID` path and body fields where FastAPI can validate them.

## Frontdoor Blackbox Test Plan
- For each changed route, a bad id gives 400/422 and no write happens. No route makes up a UUID.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/services-backend.md` (SVC-04)
