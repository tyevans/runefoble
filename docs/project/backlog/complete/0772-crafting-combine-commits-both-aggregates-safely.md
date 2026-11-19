---
id: '0772'
title: Crafting Combine Commits Both Aggregates Safely
status: Complete
created: 2026-11-17
dependencies:
- TASK-0729
governing_adrs:
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0772: Crafting Combine Commits Both Aggregates Safely

## Status
Complete

## Summary
Combine saves the crafting aggregate (reagents spent) and then the character aggregate (mishap damage) with no shared transaction. A failed second save leaves reagents spent and no damage applied.

## Problem Statement
- `CombineReagentsService` saves two aggregates in sequence (TASK-0729).

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Choose a design and record it: a process manager that reacts to the crafting event and applies damage idempotently (retry until applied), or move the mishap damage decision so one aggregate owns the outcome.
2. Make the second step idempotent by event id so a retry cannot apply damage twice.

## Frontdoor Blackbox Test Plan
- Force the character store to fail once after the crafting save. Recover the store. Assert the damage is applied exactly once and the reagents are spent once.

## Definition of Done
- No combine outcome leaves the two aggregates inconsistent after recovery.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `work/0729.md`
