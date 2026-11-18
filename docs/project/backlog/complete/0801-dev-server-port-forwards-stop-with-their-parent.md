---
id: '0801'
title: "Dev Server Port-Forwards Stop With Their Parent Process"
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0005
governing_prds: []
governing_stories: []
target_bc: tooling
target_release: 0.9.0
---

# TASK-0801: Dev Server Port-Forwards Stop With Their Parent Process

## Status
Complete

## Summary
When `scripts/dev_server.py` is killed (a test timeout or SIGKILL), its `kubectl port-forward` children stay alive and hold local ports.

## Problem Statement
- `scripts/dev_server.py` starts `kubectl port-forward` children with no process group and no parent-death signal.
- Five port-forward processes stayed alive after timed-out test runs during batch 26.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0005.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Start each port-forward in a new process group owned by the dev server, and stop the group on every exit path (normal exit, SIGTERM, SIGINT).
2. On Linux, set a parent-death signal (`prctl(PR_SET_PDEATHSIG)` through a `preexec_fn`) so a SIGKILL of the parent also stops the children.

## Frontdoor Blackbox Test Plan
- A test starts the dev server against a fake `kubectl` on PATH, kills the dev server with SIGKILL, and checks that no fake port-forward process is still alive after 5 seconds.

## Definition of Done
- The test plan passes.
- `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/drafts/round3-notes.md` batch 26 (Discovered)
