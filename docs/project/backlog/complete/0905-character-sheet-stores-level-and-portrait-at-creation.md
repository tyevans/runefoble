---
id: '0905'
title: "Character Sheet Stores Level and Portrait at Creation"
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0014
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: character_sheet
target_release: 0.9.0
---

# TASK-0905: Character Sheet Stores Level and Portrait at Creation

## Status

Complete

## Summary

The character builder offers Level and a portrait, and the user story asks for a level 4 character, but character_sheet cannot store them at creation and the gateway refuses them with 422. The user chose (2026-11-19): character_sheet stores `level` and the portrait URL at creation.

## Problem Statement

- `gateway/api/src/gateway_api/character_view.py:54-67` refuses `level != 1` and `portraitUrl` at create.
- `services/character_sheet/src/character_sheet/schemas.py`: no `level` at creation.
- `services/character_sheet/ui/src/roster/runefoble-character-builder-modal.ts:79,84` always sends `level` and `portraitUrl`.
- `e2e/steps/character_sheet_steps.ts:71-82` (`level: 4`) and `e2e/steps/session_lobby_roles_steps.ts:85-88` (`level: 3`).
- Next failure after the fix: "Equipping and Unequipping Gear" needs "Longsword +1" in the inventory, and no Given step adds it.

## Documentation & Architecture Review

- `.audit/reports/e2e-triage-1.md` gives the evidence (gateway log lines, error-context files).
- ADR-0014: user flows are verified through Playwright without backdoors or `page.route` fakes of our own services. ADR-0015: no invented values and no success shown after an error.

## Product & User Story References

None beyond the scenarios named below.

## Detailed Specification & Implementation Plan

1. The character creation event and state carry `level` (1-20, validated) and `portrait_url` (validated URL or asset reference). Read routes return them.
2. The gateway create mapping forwards them and stops refusing them. Keep refusing fields that the owner still cannot store.
3. e2e: the Background adds "Longsword +1" through `POST /api/v1/characters/{id}/inventory`.
4. Update the event catalogue and the character sheet how-to.

## Frontdoor Blackbox Test Plan

- Blackbox: create through the gateway with level 4 and a portrait, then read both back. Level 0 or 21 answers 422.
- Playwright on Kind (orchestrator): `character_sheet.feature` (4 scenarios) and the seated-player scenario of `session_lobby_roles.feature`.

## Definition of Done

- The plan is done and the tests pass. The orchestrator runs the named Playwright scenarios on Kind. Docs and CHANGELOG updated.

## Audit Provenance

- Severity: high
- Source audits: .audit/reports/e2e-triage-1.md
