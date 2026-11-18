---
id: '0715'
title: Tests Use Public Setup Instead of Repository Setters and Private Attributes
status: Refined
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
# TASK-0715: Tests Use Public Setup Instead of Repository Setters and Private Attributes

## Status
Refined. Found by the refactor audit round r1 and checked against the code by the orchestrator.

## Summary
Tests inject repositories through module setters and read or write private attributes. These are backdoors under Hard Invariant 7.

## Problem Statement
- Repository setters: `tests/test_blackbox_faction_simulation.py:62-63`, `tests/test_blackbox_faction_radar_ui.py:54-55`, `tests/test_blackbox_world_tick_durability.py:50-57`, `tests/test_blackbox_faction_resources/conftest.py:46`, `tests/test_blackbox_turf_war/conftest.py:44`, `tests/test_blackbox_west_marches_ui/conftest.py:60`, `tests/test_blackbox_west_marches.py:63`.
- `set_event_store` is called 21 times in `tests/`, some in test bodies.
- Private reads: `store._events` in `tests/test_blackbox_tabletop_physics.py:93,131`, `tests/test_blackbox_tabletop_3d.py:82,149`, `tests/test_blackbox_miniature_knockback/test_knockback_impulse_and_elevation.py:161,204`, `tests/test_blackbox_3d_dice_physics/test_cryptographic_dice_alignment.py:88`.
- Private writes: `bus._client = mock_redis` in `tests/test_websocket_modular_decomposition.py:140` and `tests/test_websocket_zanzibar_mutators.py:164`. `signaling_manager._coordinator = coord` in `tests/test_blackbox_webrtc_routing.py:43,48` and `tests/test_blackbox_webrtc_auth.py:52,64`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0014, ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Build repositories through the app lifespan, or through a public settings value that selects the in-memory store (allowed for tests only by ADR-0015 f). No setter calls remain in tests.
2. Read events from the published stream (`MockAsyncRedis.streams`) or a public query route. Replace `_client` and `_coordinator` writes with public setters.
3. Do the listed files in this slice. Leave the `set_event_store` callers outside them for a follow-up recorded in the PR.
4. Sequence after TASK-0697 (shared harness).

## Frontdoor Blackbox Test Plan
- Each changed test asserts the same events on the public stream.
- `grep -n "\._events\|\._client =\|\._coordinator =" tests` shows none in the listed files.
- The faction tick test drives `POST` on the public tick route and reads the result through the query route.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r1/tests.md`
