---
id: '0815'
title: "Each Event Class Has One Import Home and No Alias Names"
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: runefoble_events
target_release: 0.9.0
---

# TASK-0815: Each Event Class Has One Import Home and No Alias Names

## Status
Complete

## Summary
Event classes have up to five import homes (dead `events.py`, facade modules), and 25 Python alias names remain (for example `DiceRollEvent = DiceRolled`).

## Problem Statement
- Findings F1, F2, F3 in `.audit/research/libs.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0011.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Keep one public home per class (`runefoble_events.events` package or the per-context module, pick one and document it). Delete `events.py` (shadowed) and every facade re-export.
2. Delete the 25 alias assignments. Update every import in libs, services, gateway and tests directly.
3. Remove `suppress_event_type_warning` where the explicit `event_type` field makes it redundant, if eventsource-py allows it (F3); otherwise record why it stays.

## Frontdoor Blackbox Test Plan
- The full suite passes. `grep` finds no alias assignment of an event class and no second import home.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/libs.md` (F1, F2, F3)
