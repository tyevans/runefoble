---
id: '0872'
title: Blackbox Tests Restore Every Seam They Replace and Drop Dead Fixtures
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0014
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0872: Blackbox Tests Restore Every Seam They Replace and Drop Dead Fixtures

## Status
Refined.

## Summary
Some blackbox tests replace a process-wide seam and never restore it. The copilot engine that one test builds keeps its timers after the test ends. The shared helpers `seam_restorer` and `restored_seam` already exist. Use them at every site, and delete the unused audio fixtures and empty section headers.

## Problem Statement
- `tests/test_blackbox_west_marches.py:49`, `tests/test_blackbox_west_marches_prices.py:38`, `tests/test_blackbox_broad_except_load_errors.py:75`, and `tests/test_blackbox_west_marches_ui/conftest.py:36` call `set_west_marches_repo` with no restore.
- `tests/test_blackbox_watcher_copilot_restart.py:95-96`: `_restart()` calls `set_copilot_engine(build_copilot_engine())`. The autouse fixture at lines 68-90 does not keep the copilot seam. The engine stays in the process global, and its timers keep running.
- `tests/test_blackbox_stand_in_policies.py:47`: `set_spicedb_client(spicedb)` is called directly. The shared helper `shared_spicedb_client` (`tests/helpers/spicedb_factory.py:23-28`) exists for this use.
- `tests/helpers/audio_synth.py:151-163`: fixtures `shared_event_bus` and `client` set the streaming pipeline and watcher client with no restore. A grep shows that only `audio_synth.py` uses them.
- `gateway/api/tests/test_blackbox_gateway_ws_identity.py:83-88`: two verifiers are saved and restored by hand after `yield`. A `try/finally` or `seam_restorer` is safer.
- `tests/test_blackbox_app_shell_orchestration.py:43-56`: three section headers have no tests under them. The first names a line-count test that does not exist.

## Documentation & Architecture Review
- ADR-0014 (blackbox tests run through frontdoors and do not depend on leaked state).
- `tests/helpers/module_state.py:25` (`restored_seam`) and `tests/helpers/event_store_seam.py` are the approved seam helpers.

## Product & User Story References
None. Test quality work.

## Detailed Specification & Implementation Plan
1. Replace each direct `set_*` call listed above with `seam_restorer.replace(get, set, value)`. For `set_spicedb_client`, use `shared_spicedb_client`.
2. In `watcher_copilot_restart`, add `seam_restorer.keep(get_copilot_engine, set_copilot_engine)` to the autouse fixture. In its teardown, call `shutdown()` on the engine that the test left in place, before the restore.
3. Delete `shared_event_bus` and `client` from `audio_synth.py` after a grep confirms that no other file uses them.
4. In `test_blackbox_gateway_ws_identity.py`, replace the two manual restores with `seam_restorer`.
5. Delete the three empty section headers in `test_blackbox_app_shell_orchestration.py`.

## Frontdoor Blackbox Test Plan
- Existing suites pass with the same results. This covers the mcp, west marches, stand-in and ws identity suites.
- Harness test in `tests/test_blackbox_seam_restore.py`: a test replaces the copilot engine, and a later test sees the original engine again.

## Definition of Done
- No direct `set_*` seam call without a restorer in the listed files.
- `uv run pytest` and `make health-check` pass. No file over 500 lines.
- No backward-compatibility shim (DoR 9).

## Audit Provenance
- Severity: medium
- Source audits: `tests`
