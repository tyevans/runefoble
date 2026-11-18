---
id: '0802'
title: "Backlog Link Check Treats Cache-Only Folders as Missing"
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: tooling
target_release: 0.9.0
---

# TASK-0802: Backlog Link Check Treats Cache-Only Folders as Missing

## Status
Complete

## Summary
The backlog link checker accepts a cited folder that holds only `__pycache__`, so a deleted package can hide behind a leftover cache.

## Problem Statement
- `scripts/check_backlog_links.py`: a path that exists only as a folder with `__pycache__` passes the check.
- Seen twice: batch 22 and batch 27.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0014.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. A cited folder whose only content is `__pycache__` folders (at any depth) counts as missing.

## Frontdoor Blackbox Test Plan
- A test creates a temporary backlog record that cites a folder holding only `__pycache__/x.pyc`, runs the checker, and expects the citation to be reported as missing.

## Definition of Done
- The test plan passes.
- `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `.audit/drafts/round3-notes.md` batch 27 (Discovered)
