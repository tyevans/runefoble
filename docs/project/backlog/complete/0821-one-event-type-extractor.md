---
id: '0821'
title: "Event Type Extraction and Small Helpers Have One Home"
status: Complete
created: 2026-11-18
dependencies:
- TASK-0815
governing_adrs:
- ADR-0011
governing_prds: []
governing_stories: []
target_bc: runefoble_platform
target_release: 0.9.0
---

# TASK-0821: Event Type Extraction and Small Helpers Have One Home

## Status
Complete

## Summary
Event-type extraction exists in five places with different fallbacks; `utc_now` is copied three times; d20 rolls repeat in five services; two "unavailable" error families have four bases; dead platform models remain.

## Problem Statement
- Findings F4, F6, F8 in `.audit/research/libs.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0011.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. One event-type function with no silent fallback. One `utc_now`. One dice roller in `runefoble_platform`.
2. One unavailable-error base. Delete dead `BaseEntity`, `CampaignScopedEntity`, `AuthorizationError`, `GameRuleViolationError` if no caller remains.

## Frontdoor Blackbox Test Plan
- Publish and consume tests pass. An event without a type fails loudly.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/libs.md` (F4, F6, F8)
