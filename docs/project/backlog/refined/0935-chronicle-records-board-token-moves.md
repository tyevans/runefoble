---
id: '0935'
title: "The Session Chronicle Records Board Token Moves"
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0935: The Session Chronicle Records Board Token Moves

## Status

Refined. Found by the seventh full e2e run on Kind.

## Summary

The session chronicle feed reads game_session session events, and board token moves are board_state `TokenMoved` events, so a move never appeared in the feed.

## Problem Statement

- e2e `session_lobby_and_vtt.feature` "Live Token Kinematics": "the chronicle feed logs the move action" failed.

## Documentation & Architecture Review

- ADR-0015: failures are visible and quick.

## Product & User Story References

- The e2e scenarios named below.

## Detailed Specification & Implementation Plan

1. game_session consumes `TokenMoved` from `runefoble.events.board` and records `TokenMoveChronicled` (a line such as "Valeros the Bold moved to (3, 3)"). A source event id guard stops a second line on redelivery; a move for an unknown session goes to the dead-letter stream.
2. The gateway sends the line live as a `chronicle_entry` session frame; the App Shell adds it once.
3. The consumer group starts at `0`, as every consumer group in the project does, so it backfills history idempotently.

## Frontdoor Blackbox Test Plan

- Frontdoor tests: one move gives one chronicle line; a redelivery gives none; an unknown session goes to the dead-letter stream.
- Playwright on Kind: the scenario passes.

## Definition of Done

- Tests pass. Docs and CHANGELOG entry. The orchestrator runs the scenarios on Kind.

## Audit Provenance

- Severity: medium
- Source audits: .audit/work/chronicle-moves.md
