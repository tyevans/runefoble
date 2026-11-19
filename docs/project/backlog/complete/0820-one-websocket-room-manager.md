---
id: '0820'
title: "One WebSocket Room Manager and One Serve Loop"
status: Complete
created: 2026-11-18
dependencies:
- TASK-0810
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: runefoble_platform
target_release: 0.9.0
---

# TASK-0820: One WebSocket Room Manager and One Serve Loop

## Status
Complete

## Summary
Five WebSocket group managers (three in the gateway, two in services) and three copies of the socket serve loop exist.

## Problem Statement
- Findings G-04 in `.audit/research/gateways.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0015.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. Add `WebSocketGroups[K]` (register, disconnect, broadcast, dead-peer pruning) in `runefoble_platform`, and one `serve_authorized_socket` helper in `runefoble_auth.websocket`.
2. Replace the five managers and the repeated loops.

## Frontdoor Blackbox Test Plan
- Existing socket tests pass. A dead peer is pruned and the others still receive broadcasts.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/gateways.md` (G-04)
