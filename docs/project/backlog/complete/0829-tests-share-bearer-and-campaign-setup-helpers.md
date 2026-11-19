---
id: '0829'
title: "Tests Share One Bearer Helper and One Campaign Setup Helper"
status: Complete
created: 2026-11-18
dependencies:
- TASK-0827
governing_adrs:
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: tests
target_release: 0.9.0
---

# TASK-0829: Tests Share One Bearer Helper and One Campaign Setup Helper

## Status
Complete

## Summary
164 bearer helper definitions in about 90 modules and 12 copies of campaign setup.

## Problem Statement
- Findings T-01, T-02, T-10, T-17 in `.audit/research/tests.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0014.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. One `bearer(sub, issuer=...)` in `tests/helpers/ws_identity.py`; one `tests/helpers/campaign_setup.py` through public routes; one `live_upstream` builder; one event-store reset fixture.

## Frontdoor Blackbox Test Plan
- The suite passes.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/tests.md` (T-01, T-02, T-10, T-17)
