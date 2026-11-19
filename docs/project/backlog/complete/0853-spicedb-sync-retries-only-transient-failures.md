---
id: '0853'
title: SpiceDB Sync Retries Only Transient Failures
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: platform
target_release: 0.9.0
---
# TASK-0853: SpiceDB Sync Retries Only Transient Failures

## Status
Complete

## Summary
`execute_with_retry` in the auth lib catches every exception and retries it with backoff. A schema rejection is permanent. The gRPC adapter already classifies it as `AuthzSchemaError`. The retry loop still repeats it three times. The fix retries only `AuthzUnavailableError` and raises every other error at once.

## Problem Statement
- `libs/runefoble_auth/src/runefoble_auth/sync_tuples.py:48-66`: `except Exception` retries every error.
- `libs/runefoble_auth/src/runefoble_auth/grpc_adapter.py:48-53`: schema rejection maps to `AuthzSchemaError`. Outage maps to `AuthzUnavailableError`.

## Documentation & Architecture Review
- ADR-0001: SpiceDB is the authority for object permissions. A schema error is a code or data error, not an outage.
- `docs/reference/spicedb-zitadel-identity-sync.md`: the retry policy. Update it to match the code.
- TASK-0855 may remove some callers of this helper. Land TASK-0855 first, or rebase this change onto it.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. In `execute_with_retry`, catch only `AuthzUnavailableError` for retry.
2. Let every other exception propagate on the first attempt. Do not log it as a transient failure.
3. Keep the backoff and the attempt count for `AuthzUnavailableError`.

## Frontdoor Blackbox Test Plan
- Use the SpiceDB test double with a call counter. Make a write that the schema rejects. Assert one call and a 4xx or typed error from the public route (not a 503).
- Make the double return unavailable. Assert the configured retry count and a 503 from the public route.

## Definition of Done
- Only `AuthzUnavailableError` triggers a retry.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r2/libs.md` (F11)
