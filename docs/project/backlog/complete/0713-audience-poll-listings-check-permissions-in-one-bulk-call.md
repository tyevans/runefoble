---
id: '0713'
title: Audience Poll Listings Check Permissions in One Bulk Call
status: Complete
created: 2026-11-17
dependencies:
- TASK-0499
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds:
- PRD-0011
governing_stories: []
target_bc: audience_studio
target_release: 0.9.0
---
# TASK-0713: Audience Poll Listings Check Permissions in One Bulk Call

## Status
Complete

## Summary
Listing polls and proposals makes one SpiceDB call per item. The two engines also copy their listener registry and notify code, and `PollEngine` mixes timers, fan-out and presentation.

## Problem Statement
- `services/audience_studio/src/pollEngine.ts:196` calls `pollAllows` once per poll. `approvalQueue.ts:59-61` makes two checks per proposal. Both run on every list request.
- `pollEngine.ts:57-63` and `approvalQueue.ts:30-36` duplicate `onX(callback)` with `indexOf` and `splice`. `pollEngine.ts:279-288` and `approvalQueue.ts:102-111` duplicate `notify`.
- `pollEngine.ts:45-289` holds commands, timer scheduling and expiry (`schedule`, `clearTimer`, `expire`, 243-277), fan-out, presentation and queries.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0001, ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
- PRD-0011

## Detailed Specification & Implementation Plan
1. Add a bulk permission check to `spicedb/spicedbClient.ts` and `access/audienceAccess.ts` (`BulkCheckPermission` or `LookupResources`). Listings make at most one call.
2. Extract a generic `EventListeners<T>` used by both engines.
3. Extract `PollCloseScheduler` (timers, restore, expiry retry) and a presenter for `presentFor` and `viewOf`.
4. Sequence after TASK-0499. Coordinate with TASK-0441, 0455 and 0456, which add listeners to these files.

## Frontdoor Blackbox Test Plan
- A list request over N polls makes at most one bulk permission call (a fake SpiceDB client counts calls).
- `test/poll_http.test.ts` (timer close, restore after restart) and `test/authorization_http.test.ts` (list filtering) pass.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r1/audience-scripts-helm.md`
