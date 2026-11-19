---
id: '0818'
title: "Each Process Uses One SpiceDB Client From the Lib Factory"
status: Complete
created: 2026-11-18
dependencies:
- TASK-0817
governing_adrs:
- ADR-0001
governing_prds: []
governing_stories: []
target_bc: runefoble_auth
target_release: 0.9.0
---

# TASK-0818: Each Process Uses One SpiceDB Client From the Lib Factory

## Status
Complete

## Summary
game_session and character_sheet build their own SpiceDB client, so a process holds two clients and ignores `runefoble_auth.factory`.

## Problem Statement
- Findings SVC-02; tests.md T-04(b) in `.audit/research/services-backend.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0001.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Every service gets its client from `runefoble_auth.factory`. Add a public `set_spicedb_client` seam there and remove the private patch in `tests/helpers/spicedb_factory.py`.

## Frontdoor Blackbox Test Plan
- Tests that swap the client through the public seam reach every service route.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/services-backend.md` (SVC-02; tests.md T-04(b))
