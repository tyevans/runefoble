---
id: '0877'
title: Store Outage Helper Records Appends and Replaces Copied Outage Stubs
status: Refined
created: 2026-11-18
dependencies:
- TASK-0872
governing_adrs:
- ADR-0011
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0877: Store Outage Helper Records Appends and Replaces Copied Outage Stubs

## Status
Refined.

## Summary
The seam helper `store_outage()` exists, but five test files copy the outage stub and the recording wrapper. Add a `record_appends` option to `store_outage()`. Replace the copies with it.

## Problem Statement
- `store_outage()` is at `tests/helpers/event_store_seam.py:31`. Five files use it.
- `_connection_refused` is defined again in `tests/test_blackbox_voice_duplex_state.py:42`, `tests/test_blackbox_voice_room_load_errors.py:38`, `tests/test_blackbox_broad_except_load_errors.py:47` and `tests/test_blackbox_aggregate_load_errors.py:41`. It is inline in `tests/test_blackbox_faction_resources/test_resource_operations.py:120`.
- The recording-append wrapper is copied in `tests/test_blackbox_voice_duplex_state.py:93-101` and `:122-130`, and in `tests/test_blackbox_voice_telemetry.py:34-54`.
- `tests/test_blackbox_voice_room_load_errors.py:83` and `:104` patch `read_stream` with `monkeypatch.setattr` on the live store.

## Documentation & Architecture Review
- ADR-0011 (event store reads and writes). ADR-0014 (outage tests run through the store seam).

## Product & User Story References
None. Test helper work.

## Detailed Specification & Implementation Plan
1. Add a `record_appends: bool = False` parameter to `store_outage()`. When it is true, the context manager yields the list of recorded append calls.
2. Delete the four `_connection_refused` copies and the inline copy. Use `store_outage()` instead.
3. Delete the two recording wrappers in `test_blackbox_voice_duplex_state.py` and the wrapper in `test_blackbox_voice_telemetry.py`. Use the yielded list.
4. Replace the `monkeypatch.setattr(..., "read_stream", ...)` calls with `store_outage()`.

## Frontdoor Blackbox Test Plan
- The same 503 responses and "saves nothing" assertions pass.
- After the outage block, a read sees the stored history. Assert this in one test.

## Definition of Done
- One outage stub in `tests/helpers/event_store_seam.py`.
- No `_connection_refused` definition outside that helper.
- `uv run pytest` passes. No file over 500 lines.
- No backward-compatibility shim (DoR 9).

## Audit Provenance
- Severity: low
- Source audits: `tests`
