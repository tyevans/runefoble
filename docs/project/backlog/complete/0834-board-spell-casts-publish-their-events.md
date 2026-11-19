---
id: '0834'
title: "Board Spell Casts Publish Their Events and Soundscape Reacts"
status: Complete
created: 2026-11-19
dependencies:
- TASK-0814
governing_adrs:
- ADR-0006
- ADR-0011
governing_prds:
- PRD-0001
governing_stories: []
target_bc: board_state
target_release: 0.9.0
---

# TASK-0834: Board Spell Casts Publish Their Events and Soundscape Reacts

## Status
Complete

## Summary
The board cast paths save the board but never publish `SpellCast` or `AreaEffectExploded`, so no other bounded context can react to a spell.

## Problem Statement
- `services/board_state/src/board_state/routers/vfx.py:54-62` and `routers/previews_ws_spells.py:56-67` call `repo.save(board)` only.
- The events are raised in `board_state/spells.py:57` and `:90`.
- TASK-0438 could not add the soundscape handlers for these two events.

## Documentation & Architecture Review
- TASK-0814 added one save-and-publish helper used by the move routes. ADR-0006 (Redis Streams), ADR-0011.

## Product & User Story References
PRD-0001.

## Detailed Specification & Implementation Plan
1. Both cast paths save and publish through the shared save-and-publish helper.
2. Add soundscape handlers for `runefoble.events.board.spell_cast` and `runefoble.events.board.area_effect_exploded`, reusing the cue helpers in `soundscape/tactical_cues.py`.

## Frontdoor Blackbox Test Plan
- A cast through the REST route and through the socket publishes one `spell_cast` (and one `area_effect_exploded` for an area spell) on the board stream.
- Soundscape receives each event and its public state shows the cue.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0438.md` (Discovered item 1)
