---
id: '0908'
title: "UI State Changes Replace Objects and Never Show Success After an Error"
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0908: UI State Changes Replace Objects and Never Show Success After an Error

## Status

Complete

## Summary

Some UI code changes a reactive object in place, so a child element that gets the same reference does not render again. Some catch blocks set a success state after an error. Find every case and fix it.

## Problem Statement

- `services/game_session/ui/src/caravan/caravan_api.ts:83-84` sets `contract.status = 'in_transit'` in place; `runefoble-caravan-board.ts:134-135` passes the same reference; the card (`caravan/contract_card.ts:63`) does not render again. Failing scenario: caravan_board "dispatch succeeds".
- `runefoble-caravan-board.ts:76-77` sets `status = 'accepted'` in a catch block.

## Documentation & Architecture Review

- `.audit/reports/e2e-triage-1.md` gives the evidence (gateway log lines, error-context files).
- ADR-0014: user flows are verified through Playwright without backdoors or `page.route` fakes of our own services. ADR-0015: no invented values and no success shown after an error.

## Product & User Story References

None beyond the scenarios named below.

## Detailed Specification & Implementation Plan

1. Caravan: after a 2xx reply, replace the contract with a new object (or read the list again). Remove the success-after-error assignment.
2. Scan `services/*/ui/src` and `frontend/src` for in-place changes of objects or arrays passed to child elements, and for state set to a success value inside `catch`. Fix each one.
3. Add a note to `docs/how-to/develop-lit-components-in-storybook.md`.

## Frontdoor Blackbox Test Plan

- DOM test: after dispatch, the card badge shows "in transit". After a failed accept, the card keeps its old status and shows the error.
- Playwright on Kind (orchestrator): `caravan_board.feature`.

## Definition of Done

- The plan is done and the tests pass. The orchestrator runs the named Playwright scenarios on Kind. Docs and CHANGELOG updated.

## Audit Provenance

- Severity: medium
- Source audits: .audit/reports/e2e-triage-1.md
