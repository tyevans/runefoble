---
id: '0825'
title: "UI HTTP, Auth and Socket Helpers Live in libs/runefoble_ui"
status: Complete
created: 2026-11-18
dependencies:
- TASK-0812
- TASK-0824
governing_adrs:
- ADR-0004
- ADR-0013
governing_prds: []
governing_stories: []
target_bc: runefoble_ui
target_release: 0.9.0
---

# TASK-0825: UI HTTP, Auth and Socket Helpers Live in libs/runefoble_ui

## Status
Complete

## Summary
HTTP error and JSON plumbing exists in four or five versions, and bearer and WebSocket URL helpers repeat about seven times.

## Problem Statement
- Findings F-05, F-06 in `.audit/research/frontend-ui.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0004, ADR-0013.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Add one typed fetch helper (bearer, JSON, typed error) and one socket URL helper to `libs/runefoble_ui`. Replace the copies.

## Frontdoor Blackbox Test Plan
- Vitest tests of the helpers; package tests pass.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/frontend-ui.md` (F-05, F-06)
