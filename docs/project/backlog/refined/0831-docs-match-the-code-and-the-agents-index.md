---
id: '0831'
title: "Docs Match the Code and the AGENTS.md Index"
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: docs
target_release: 0.9.0
---

# TASK-0831: Docs Match the Code and the AGENTS.md Index

## Status
Refined

## Summary
Reference pages document deleted projections, a how-to contradicts Hard Invariant 3, AGENTS.md misses 10 reference pages and the runefoble_ui row, and a tracked generated changelog copy is stale.

## Problem Statement
- Findings D1, D2, D3, D4, D5, D6, D7, D8 in `.audit/research/docs.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0014.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Fix D1 to D5. Stop tracking the generated `docs/changelog.md` and `docs/operating-manual.md` copies if the docs build creates them (D6). Merge the two Playwright BDD how-tos (D7). Move reference sections out of how-tos where cheap (D8).

## Frontdoor Blackbox Test Plan
- `scripts/check_agents_index.py` passes; the docs build passes; links resolve.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/docs.md` (D1, D2, D3, D4, D5, D6, D7, D8)
