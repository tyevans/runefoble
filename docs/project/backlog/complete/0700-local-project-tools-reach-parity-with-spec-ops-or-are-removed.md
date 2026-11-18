---
id: '0700'
title: Local Project Tools Reach Parity With spec-ops or Are Removed
status: Complete
created: 2026-11-17
dependencies:
- TASK-0668
governing_adrs:
- ADR-0003
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0700: Local Project Tools Reach Parity With spec-ops or Are Removed

## Status
Complete

## Summary
`tools/` keeps a PRD pipeline, a backlog engine and a project visualizer that spec-ops also provides. Two tools for one job drift apart.

## Problem Statement
- `make prd-audit|decompose|create|sync`: `spec-ops prd audit` and the local audit report different things.
- `make backlog-worker`: no dry-run comparison with `spec-ops worker --dry-run` and `spec-ops queue`.
- `make visualize-project*`: no side-by-side render with `spec-ops visualizer`. Tasks 0235, 0291, 0328, 0335 and 0346 wait on this.
- The spec-ops pin is in CI only.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0003.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. For each tool, run both on the same tree and record the comparison in `docs/reference/cli-interfaces.md`.
2. Where spec-ops covers the job, point the make target at spec-ops and delete the local tool and its tests.
3. Where it does not, file the gap as a spec-ops task in `~/workspace/spec-ops` and record why the local tool stays.
4. Keep one spec-ops pin source and reference it from AGENTS.md, CI and the CLI reference.

## Frontdoor Blackbox Test Plan
- Make target smoke runs through the public CLI on a fixture tree (no source-text tests).

## Definition of Done
- Each local tool is either deleted or has a recorded reason to stay.
- One spec-ops pin source.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `work/0668.md`
