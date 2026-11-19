---
id: '0906'
title: "The Session View Shows a No-Battlemap-Yet State When the Session Has No Board"
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0013
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: frontend
target_release: 0.9.0
---

# TASK-0906: The Session View Shows a No-Battlemap-Yet State When the Session Has No Board

## Status

Refined.

## Summary

The live session view fails as a whole when board_state answers 404 for the session board, so the chronicle feed and roster do not show. The user chose (2026-11-19): a missing board is a typed empty state, and the other panels still render.

## Problem Statement

- `frontend/src/app/session-data-loader.ts:33-46`: any `fetchBoardState` failure calls `failLoad` and replaces the whole view.
- `services/board_state/src/board_state/dependencies.py:54-64`: 404 until a board is created.
- Failing scenario: `session_chronicle_feed.feature`.

## Documentation & Architecture Review

- `.audit/reports/e2e-triage-1.md` gives the evidence (gateway log lines, error-context files).
- ADR-0014: user flows are verified through Playwright without backdoors or `page.route` fakes of our own services. ADR-0015: no invented values and no success shown after an error.

## Product & User Story References

None beyond the scenarios named below.

## Detailed Specification & Implementation Plan

1. The board fetch maps 404 to a typed `no_board` result. Other errors (401, 403, 5xx, network) keep their current error handling.
2. The session view renders the feed, roster and other panels, and shows "No battlemap yet" in the board area. A DM sees a hint to set up a map.
3. Storybook story for the no-board state.

## Frontdoor Blackbox Test Plan

- Frontend unit test: 404 gives `no_board`; 503 still gives the error view.
- Playwright on Kind (orchestrator): `session_chronicle_feed.feature`.

## Definition of Done

- The plan is done and the tests pass. The orchestrator runs the named Playwright scenarios on Kind. Docs and CHANGELOG updated.

## Audit Provenance

- Severity: medium
- Source audits: .audit/reports/e2e-triage-1.md
