---
id: '0796'
title: Auth Sync Health Reports Failures Honestly
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: runefoble_auth
target_release: 0.9.0
---

# TASK-0796: Auth Sync Health Reports Failures Honestly

## Status
Refined. Found during batch 23 integration, 2026-11-17.

## Summary
The identity sync health check catches every exception and returns a dict, and the gateway fills missing keys with `healthy` and `mock`. A broken sync can report healthy.

## Problem Statement
- `libs/runefoble_auth/src/runefoble_auth/sync.py:132`: broad `except Exception` in `check_health`.
- `gateway/api/src/gateway_api/auth_sync.py:65-67`: defaults `status` to `healthy` and `backend` to `mock`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0001, ADR-0015.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Catch only the transport and SpiceDB errors and report them as `unhealthy` with the cause.
2. The gateway treats a missing key as a malformed reply and reports `unhealthy`.

## Frontdoor Blackbox Test Plan
- With SpiceDB unreachable, the sync health route reports `unhealthy`.
- A reply without `status` reports `unhealthy` through the gateway.

## Definition of Done
- The test plan passes.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0674.md` (Discovered)
