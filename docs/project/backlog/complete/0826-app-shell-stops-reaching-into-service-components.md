---
id: '0826'
title: "The App Shell Stops Reaching Into Service Component Internals"
status: Complete
created: 2026-11-18
dependencies:
- TASK-0824
governing_adrs:
- ADR-0013
governing_prds: []
governing_stories: []
target_bc: frontend
target_release: 0.9.0
---

# TASK-0826: The App Shell Stops Reaching Into Service Component Internals

## Status
Complete

## Summary
`frontend/src/vtt-mesh-handlers.ts` queries service component tags and drives them directly, which couples the shell to service internals.

## Problem Statement
- Findings F-07 in `.audit/research/frontend-ui.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0013.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Replace direct tag queries with documented custom events or the plugin slot contract.

## Frontdoor Blackbox Test Plan
- App Shell tests and the VTT Playwright scenarios pass.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/frontend-ui.md` (F-07)
