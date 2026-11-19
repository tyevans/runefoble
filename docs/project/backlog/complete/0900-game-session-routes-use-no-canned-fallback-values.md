---
id: '0900'
title: Campfire and Tavern Routes Use No Canned Fallback Values
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0900: Campfire and Tavern Routes Use No Canned Fallback Values

## Status

Complete

## Summary

The campfire rest route heals a fixed list of names when the session has no participants. The tavern open-table request has a substitute establishment id. Both invent data (ADR-0015).

## Problem Statement

- `services/game_session/src/game_session/routers/campfire.py:92-93`: `participants_healed = ["Bram the Tinkerer", "Valeros", "Kyra"]` when no participant is found.
- `services/game_session/src/game_session/routers/tavern.py:76`: `establishment_id: str = "est-default"`.

## Documentation & Architecture Review

- [ADR-0021](../../adrs/accepted/adr-0021-game-session-internal-bounded-contexts.md): game_session packages, ports-only import rule, migration order (D7).
- ADR-0015: no substitute values, no shims (DoR 9).

## Product & User Story References

None. Internal structure or data integrity.

## Detailed Specification & Implementation Plan

1. Campfire: with no participants, answer 422 with a clear detail (or heal nobody, if the use case says an empty rest is valid; record the choice in the how-to). Never invent names.
2. Tavern: `establishment_id` is required. A missing value answers 422.
3. Update `docs/how-to/run-campfire-rests-and-alchemical-crafting.md` and `docs/how-to/run-tavern-minigames-and-merchant-haggling.md`.

## Frontdoor Blackbox Test Plan

- A campfire rest in a session with no participants and no ids in the body never returns the three canned names.
- `POST` open table without `establishment_id` answers 422.

## Definition of Done

- The plan is done. All game_session blackbox suites stay green. Docs updated. CHANGELOG entry.

## Audit Provenance

- Severity: medium
- Source audits: .audit/work/0753.md
