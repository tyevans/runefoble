---
id: '0874'
title: Blackbox Tests Set Up Aggregate State Through Public Routes
status: Complete
created: 2026-11-18
dependencies:
- TASK-0876
- TASK-0877
governing_adrs:
- ADR-0011
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0874: Blackbox Tests Set Up Aggregate State Through Public Routes

## Status
Complete

## Summary
Several blackbox tests run domain methods and call `repo.save` before the HTTP call. The HTTP path never creates the state. Round-trip checks belong in unit tests. Blackbox tests must create state through public routes and read it back through public routes.

## Problem Statement
- `tests/test_blackbox_tactile_board.py:83`: about eight domain methods, then `repo.save(board)`, then `repo.load`.
- `tests/test_blackbox_spell_vfx/test_speech_vfx_triggers.py:90`: `_run(repo.save(...))` for a board with a cast spell.
- `tests/test_blackbox_character_campaign_assignment.py:110` and `:124`: `repo.save` for a character.
- `tests/test_blackbox_soundscape_aggregate_decomposition.py:138`: `repo.save` for a soundscape aggregate.
- `tests/test_blackbox_voice_room_load_errors.py:30-46`: a voice room is seeded with `repo.save`, then the `fresh_coordinator` fixture sets up the outage.
- `tests/test_blackbox_aggregate_load_errors.py:85` and `:185`: fresh aggregates are saved directly.

## Documentation & Architecture Review
- ADR-0011 (state changes flow through aggregates and the repository). ADR-0014 (blackbox setup uses frontdoors).
- `tests/test_event_sourcing.py` and `tests/test_character_aggregate.py` already cover aggregate round trips.

## Product & User Story References
None. Test quality work.

## Detailed Specification & Implementation Plan
1. Move each pure save-then-load assertion into a unit test in `tests/test_event_sourcing.py` or `tests/test_character_aggregate.py`. Keep the assertions. Do not delete them.
2. For each blackbox test, create state through the public `POST` route and read it back through the public `GET` route.
3. For the voice room, join the peer through `/api/v1/voice/rooms` before the outage seam starts.
4. Where a domain method has no HTTP route, move that test to a unit test file. Rename it to say so. The blackbox file keeps only route-driven cases.

## Frontdoor Blackbox Test Plan
- Each rewritten test creates its state with HTTP calls only.
- The same assertions run after the seam is restored. Use `restored_seam` from `tests/helpers/event_store_seam.py`, and read back with `GET`.
- The 503 and "saves nothing" assertions stay unchanged.

## Definition of Done
- No `repo.save` or `repo.load` in the listed blackbox files.
- Unit tests cover each removed round trip.
- `uv run pytest` and `make health-check` pass. No file over 500 lines.
- No backward-compatibility shim (DoR 9).

## Audit Provenance
- Severity: medium
- Source audits: `tests`
