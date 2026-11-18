---
id: '0701'
title: Event Wire Names Follow One Identifier Rule
status: Complete
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
# TASK-0701: Event Wire Names Follow One Identifier Rule

## Status
Complete

## Summary
About 132 event classes set an `event_type` that does not follow `runefoble.events.<bc>.<snake_case>`. Consumers match on these strings, so this is a planned wire-contract change.

## Problem Statement
- See `.audit/work/0579.md` Follow-ups item 2 and `docs/reference/event-identifiers.md`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0006, ADR-0011.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Generate the rename list from the event registry.
2. Rename producers and consumers in one change per bounded context. No alias types (DoR 9).
3. Regenerate `docs/reference/event-identifiers.md` with `scripts/generate_event_catalogue.py`.
4. Coordinate with TASK-0487 before touching alias modules.

## Frontdoor Blackbox Test Plan
- For each bounded context, publish through the public route and assert the consumer projection changes (consumer still matches after the rename).

## Definition of Done
- Every registered event follows the rule. The catalogue states the rule.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `work/0579.md`
