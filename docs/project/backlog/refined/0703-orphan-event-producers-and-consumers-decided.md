---
id: '0703'
title: Orphan Event Producers and Consumers Are Decided
status: Refined
created: 2026-11-17
dependencies:
- TASK-0579
governing_adrs:
- ADR-0006
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0703: Orphan Event Producers and Consumers Are Decided

## Status
Refined. Slice of TASK-0579 (Follow-ups items 1 and 5).

## Summary
17 event classes have no producer and 38 have no consumer. Each needs a producer, a consumer, or deletion.

## Problem Statement
- See `.audit/work/0579.md`. Watcher action events depend on TASK-0568. `CombatRoundAdvanced` relates to TASK-0574.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0006, ADR-0011.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Decide each class. Add the producer or consumer, or delete the class.
2. Record the decisions in the catalogue.
3. Add the wardrobe end-to-end read test: create a wardrobe variant, then read the character wardrobe through the public route.

## Frontdoor Blackbox Test Plan
- One frontdoor test per added producer or consumer.
- Wardrobe variant appears in the public wardrobe read.

## Definition of Done
- No registered event lacks a producer or a consumer without a recorded reason.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `work/0579.md`
