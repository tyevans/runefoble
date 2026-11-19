---
id: '0714'
title: Test Module State Is Restored and Collection Fails on Import Errors
status: Complete
created: 2026-11-17
dependencies:
- TASK-0697
governing_adrs:
- ADR-0014
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0714: Test Module State Is Restored and Collection Fails on Import Errors

## Status
Complete

## Summary
Many fixtures restore module globals to a new object or to `None`. After a `None` teardown the SpiceDB getter builds a real client, so a later test without a mock can reach a real endpoint. The root conftest hides import failures with `suppress(Exception)`.

## Problem Statement
- `conftest.py:170-176` and `:181-183`: `contextlib.suppress(Exception)` around `importlib.import_module` and `set_spicedb_client`.
- `tests/test_blackbox_vocal_modulator_ui/test_vocal_modulator_ui.py:36-43`: fixture mutates the voice coordinator with no `yield` and no teardown.
- Teardown sets `SpiceDBClient()`: `tests/test_blackbox_dm_traps_ui/conftest.py:51`, `tests/test_blackbox_faction_resources/conftest.py:48`, `tests/test_blackbox_uvtt_doors_lights/conftest.py:40`, `tests/test_blackbox_webrtc_routing.py:50`, `tests/test_blackbox_webrtc_auth.py:66`, and six more files.
- Teardown sets `None` in 26 files, for example `tests/test_blackbox_settlement_haven/conftest.py:36`. `services/game_session/src/game_session/dependencies.py:138-147` (removed) builds a real `SpiceDBClient` when the global is `None`.
- `conftest.py:245-247` resets `game_session_upstream` to `None`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0014, ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `tests/helpers/module_state.py` with a context manager and a fixture that save the previous value of a module global and restore it.
2. Replace every `SpiceDBClient()` and `None` teardown with it. Fix the vocal modulator fixture.
3. In `conftest.py`, import each module in the SPICEDB list once at collection with no `suppress`. Assert the setter exists.
4. If TASK-0697 replaces the registries, fold step 3 into it and keep step 1 and 2 here. Sequence after TASK-0697 to avoid conflicts.
5. Run each affected directory alone and in reverse order.

## Frontdoor Blackbox Test Plan
- Each affected file passes alone and with reversed collection order.
- A test after a restore sees the previous mock client from `get_spicedb_client()`, not a real client.
- A test with a misspelled module name in the list fails at collection.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r1/tests.md`
