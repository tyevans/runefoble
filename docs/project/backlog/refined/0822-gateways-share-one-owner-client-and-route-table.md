---
id: '0822'
title: "Both Gateways Share One Owner Client and the API Gateway Uses a Route Table"
status: Refined
created: 2026-11-18
dependencies:
- TASK-0807
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: gateway_api
target_release: 0.9.0
---

# TASK-0822: Both Gateways Share One Owner Client and the API Gateway Uses a Route Table

## Status
Refined

## Summary
gateway_api and gateway_mcp each have a client stack for the same owners, and about 83 pass-through proxy routes repeat the same forward code.

## Problem Statement
- Findings G-02, G-03, G-12 in `.audit/research/gateways.md` give every location (path:line). Check each against main before you change it.

## Documentation & Architecture Review
- AGENTS.md (SOLID, DDD, Hard Invariants 1, 2, 6, 7; DoR 9: no shims or aliases).
- ADR-0015.

## Product & User Story References
None. Refactor and consolidation chosen by the user on 2026-11-18.

## Detailed Specification & Implementation Plan
1. One typed owner client in `libs/runefoble_platform/service_client` used by both gateways. Delete `gateway_mcp/owning_services.py` duplicates.
2. A declarative route table for pure pass-through routes; keep hand-written routes only where they add a check.
3. Fix G-12 (dropped campaign title, unguarded `json.loads`).

## Frontdoor Blackbox Test Plan
- The gateway proxy tests pass. Each route in the table forwards status and body, and maps an unreachable owner to 503.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: refactor
- Source audits: `.audit/research/gateways.md` (G-02, G-03, G-12)
