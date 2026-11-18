---
id: '0830'
title: "Tests Close Backdoors Into Private State"
status: Refined
created: 2026-11-18
dependencies:
- TASK-0818
- TASK-0829
governing_adrs:
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: tests
target_release: 0.9.0
---

# TASK-0830: Tests Close Backdoors Into Private State

## Status
Refined

## Summary
Tests write private attributes (`_coordinator`, FastMCP `_tool_manager`), reset seams to None in 36 places, and write a board DM tuple in 27 copies.

## Problem Statement
- Findings T-04, T-05, T-06, T-07, T-08, T-09, T-20 in `.audit/research/tests.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0014.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Use public seams and `restored_seam`; check MCP tools through public `tools/list` and `tools/call`; create the DM through `POST /api/v1/campaigns`; keep one Redis double.

## Frontdoor Blackbox Test Plan
- The suite passes; `grep` finds no `_tool_manager` or `._coordinator` in tests.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/tests.md` (T-04, T-05, T-06, T-07, T-08, T-09, T-20)
