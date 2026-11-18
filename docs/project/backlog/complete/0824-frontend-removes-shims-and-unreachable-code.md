---
id: '0824'
title: "The Frontend Removes Forwarding Shims and Unreachable Code"
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0013
governing_prds: []
governing_stories: []
target_bc: frontend
target_release: 0.9.0
---

# TASK-0824: The Frontend Removes Forwarding Shims and Unreachable Code

## Status
Complete

## Summary
28 "App Shell backwards compatibility" forwarding shims, a dead barrel, and about 2,000 unreachable lines remain. 20 advertised tags are never rendered.

## Problem Statement
- Findings F-03, F-04, F-08 in `.audit/research/frontend-ui.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0013.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Delete the shims and the dead barrel; import the owner packages directly.
2. Delete unreachable modules (for example `frontend/src/services/webrtc-*.ts`) and their tests.
3. For each advertised but unmounted tag, mount it or stop advertising it (one list in the report).

## Frontdoor Blackbox Test Plan
- `pnpm run build`, the package tests and the Storybook build pass.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/frontend-ui.md` (F-03, F-04, F-08)
