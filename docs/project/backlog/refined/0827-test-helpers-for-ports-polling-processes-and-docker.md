---
id: '0827'
title: "Shared Test Helpers for Ports, Polling, Processes and Docker"
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: tests
target_release: 0.9.0
---

# TASK-0827: Shared Test Helpers for Ports, Polling, Processes and Docker

## Status
Refined

## Summary
15 free-port helpers, 78 subprocess calls without a timeout, 10 raw node-suite runners, 10 polling helpers and three Docker plumbing paths.

## Problem Statement
- Findings T-12, T-13, T-14, T-15, T-16 in `.audit/research/tests.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0014.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Add `tests/helpers/ports.py`, `polling.py`, `process.py` (timeout required), `node_suite.py` (lock and process-group kill, like `frontend_suite.py`) and `docker.py`. Replace the copies.

## Frontdoor Blackbox Test Plan
- The suite passes in both make test phases. `grep` finds no subprocess call without a timeout in tests/.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/tests.md` (T-12, T-13, T-14, T-15, T-16)
