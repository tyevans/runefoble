---
id: '0901'
title: Session Access Uses the game_session Campaign Relation
status: Proposed
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0901: Session Access Uses the game_session Campaign Relation

## Status

Proposed.

## Summary

`auth/session_access.py` loads the session aggregate to find the campaign and then checks `campaign.play`. The `game_session#campaign` relation in `runefoble.zed` can compute this in SpiceDB.

## Problem Statement

- `services/game_session/src/game_session/auth/session_access.py:20-28`.

## Documentation & Architecture Review

- [ADR-0021](../../adrs/accepted/adr-0021-game-session-internal-bounded-contexts.md): game_session packages, ports-only import rule, migration order (D7).
- ADR-0015: no substitute values, no shims (DoR 9).

## Product & User Story References

None. Internal structure or data integrity.

## Detailed Specification & Implementation Plan

1. Confirm that session create writes the `game_session#campaign` tuple and that `participate` includes the campaign path in `runefoble.zed`.
2. If yes, delete the aggregate load and check `participate` only. If no, write the tuple at create and record it.

## Frontdoor Blackbox Test Plan

- A campaign player can act in a session of the campaign. A stranger gets 403. A session with no campaign gives no campaign grant.

## Definition of Done

- The plan is done. All game_session blackbox suites stay green. Docs updated. CHANGELOG entry.

## Audit Provenance

- Severity: low
- Source audits: .audit/work/0753.md
