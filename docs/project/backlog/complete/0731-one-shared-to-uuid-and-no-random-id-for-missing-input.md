---
id: '0731'
title: One Shared to_uuid Helper That Rejects a Missing Identifier
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0731: One Shared to_uuid Helper That Rejects a Missing Identifier

## Status
Complete

## Summary
Four services each define `to_uuid`. All four return a random `uuid4()` for `None`. A missing identifier becomes a new identity with no error.

## Problem Statement
- Copies: `services/the_watcher/src/the_watcher/dependencies.py:180-189`, `services/the_watcher/src/the_watcher/simulation_engine.py:59-67`, `services/voice_agent/src/voice_agent/room_aggregate.py:26-35`, `services/voice_agent/src/voice_agent/stt.py:47-56`. Two more copies sit in `game_session` (`settlement/workers/loaders.py`, `minigame_rules.py`).
- The docstring says the conversion is deterministic. It is not for `None`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- Run `grep -rn "def to_uuid" services libs` and `grep -rn "to_uuid(" services` before the change. List each caller that can pass `None`.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `libs/runefoble_platform/src/runefoble_platform/ids.py` (removed) with one `to_uuid(value: str | UUID) -> UUID`. `None` raises `ValueError`. A non-UUID string maps through `uuid5` as today. The file was never created. TASK-0816 put the helper in `runefoble_platform.identifiers`.
2. Update every call site in `services/` (all six copies). Delete the old functions. Add no re-export (DoR 9).
3. Each caller that can receive `None` handles the missing id explicitly: reject the request with 422, or carry a null value. Do not create a random identity.

## Frontdoor Blackbox Test Plan
- Post a speech request without `campaign_id` through the public Watcher route. Assert that the event carries a null campaign and that no random campaign id appears.
- Existing session and speech blackbox suites pass.

## Definition of Done
- `grep -rn "def to_uuid"` finds exactly one definition.
- A unit test covers UUID, string, and `None` inputs.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `watcher-voice-inference.md (F3)`
