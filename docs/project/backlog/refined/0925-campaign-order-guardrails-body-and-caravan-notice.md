---
id: '0925'
title: Campaign List Order, Guardrails Save Body and Caravan Notice Text
status: Refined
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0014
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0925: Campaign List Order, Guardrails Save Body and Caravan Notice Text

## Status

Refined. Found by the second full e2e run on Kind (`.audit/reports/e2e-triage-2.md`).

## Summary

Three small defects. The campaign list is sorted by random campaign id, so its order changes between callers. The guardrails save sends `characterId` in the PUT body, and the strict policy model refuses it with 422. Two caravan scenarios expect a trailing period that the gateway detail does not have.

## Problem Statement

- `services/game_session/src/game_session/campaign/service_campaigns.py:203`: `sorted(granted)` sorts by random UUID4.
- `frontend/src/character-sheet-handlers.ts` `handleGuardrailsSaved` sends the whole event detail, including `characterId`.
- `e2e/features/caravan_board.feature:25,41` against `gateway/api/src/gateway_api/upstream_errors.py:25`.

## Documentation & Architecture Review

- `docs/how-to/manage-campaign-lifecycle-and-invites.md` (campaign list).

## Product & User Story References

None beyond the scenarios named.

## Detailed Specification & Implementation Plan

1. Sort the campaign list by `created_at`, then id.
2. The guardrails handler sends only the policy fields.
3. The caravan steps match the real gateway detail.

## Frontdoor Blackbox Test Plan

- Blackbox: six campaigns list in creation order.
- Frontend unit: the guardrails PUT body has no `characterId`.
- Playwright on Kind (orchestrator): app_shell_routing_state, character_sheet guardrails, caravan_board 503 scenarios.

## Definition of Done

- Tests pass. Docs updated. CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: medium
- Source audits: .audit/reports/e2e-triage-2.md
