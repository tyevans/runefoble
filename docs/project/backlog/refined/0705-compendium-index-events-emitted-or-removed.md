---
id: '0705'
title: Compendium Index Events Are Emitted or Removed
status: Refined
created: 2026-11-17
dependencies:
- TASK-0579
governing_adrs:
- ADR-0006
governing_prds: []
governing_stories: []
target_bc: rules_compendium
target_release: 0.9.0
---
# TASK-0705: Compendium Index Events Are Emitted or Removed

## Status
Refined. Slice of TASK-0579 (Follow-ups item 4).

## Summary
`MonsterIndexed`, `SpellIndexed` and `ConditionIndexed` have no producer in production code.

## Problem Statement
- See `.audit/work/0579.md` Follow-ups item 4.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0006.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Decide: emit them from the compendium indexing path, or delete them.
2. If emitted, document them in the events reference.

## Frontdoor Blackbox Test Plan
- If emitted: index an entry through the public route and assert the event on the stream.

## Definition of Done
- No unused compendium index event class remains.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `work/0579.md`
