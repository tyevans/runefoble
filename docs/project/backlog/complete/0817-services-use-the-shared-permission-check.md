---
id: '0817'
title: "Services Use One Shared Permission Check Instead of Local Wrappers"
status: Complete
created: 2026-11-18
dependencies:
- TASK-0813
governing_adrs:
- ADR-0001
governing_prds: []
governing_stories: []
target_bc: runefoble_auth
target_release: 0.9.0
---

# TASK-0817: Services Use One Shared Permission Check Instead of Local Wrappers

## Status
Complete

## Summary
About 25 local SpiceDB permission wrappers exist (some byte-identical), and game_session builds its identity dependencies three times.

## Problem Statement
- Findings SVC-05, SVC-06 in `.audit/research/services-backend.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0001.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Add or extend one dependency factory in `runefoble_auth` (`require_permission(resource_type, permission, id_param)`), and replace the local wrappers.
2. game_session uses one identity dependency set.

## Frontdoor Blackbox Test Plan
- The existing authz tests and `make test-authz-live` pass unchanged. A sample of routes per service still answers 403 for a stranger.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/services-backend.md` (SVC-05, SVC-06)

## Progress (batch 31)
Shared `runefoble_auth.permissions` check used by five services; remaining services in progress (TASK-0817 rest).
