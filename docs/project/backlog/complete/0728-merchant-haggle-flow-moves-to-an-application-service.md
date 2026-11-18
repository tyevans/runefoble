---
id: '0728'
title: Merchant Haggle Flow Moves to an Application Service and Merchants Are Created by Command
status: Complete
created: 2026-11-17
dependencies:
- TASK-0561
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds:
- PRD-0024
governing_stories:
- US-0047
- US-0075
target_bc: game_session
target_release: 0.9.0
---
# TASK-0728: Merchant Haggle Flow Moves to an Application Service and Merchants Are Created by Command

## Status
Complete

## Summary
The tavern router loads, creates, mutates, and saves merchants itself. It writes aggregate state outside `@handles` methods and returns a canned merchant on any error. This breaks Hard Invariant 2 and hides storage outages.

## Problem Statement
- `services/game_session/src/game_session/routers/tavern.py:266-275`: `haggle_merchant` catches any load error, builds a new `MerchantAggregate`, and sets `state.merchant_id`, `temperament`, and `name` directly. A storage outage creates a new merchant with the same id.
- `tavern.py:313-322`: `get_merchant` returns a hard-coded payload (`Local Merchant`, `shrewd`, `0.0`) on any error.
- `tavern.py:193-194` and `:246-247`: any minigame load error becomes HTTP 404.
- `tavern.py:254-304` holds the haggle orchestration (load, negotiate, save, publish). `_check_session_auth` (`:83-102`) holds a two-step permission policy in the router.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0011, ADR-0015.
- `docs/how-to/define-event-sourced-aggregates.md` and `docs/how-to/run-tavern-minigames-and-merchant-haggling.md`.
- TASK-0561 owns the load-helper pattern. The error path edits for `tavern.py` are an addendum to 0561 (see the index). This task owns the structural change.

## Product & User Story References
- PRD-0024
- US-0047
- US-0075

## Detailed Specification & Implementation Plan
1. Add a `MerchantAggregate` creation command (with a `@handles` event) that sets id, temperament, and name. Remove direct `aggregate.state.*` writes from the router.
2. Add `game_session/merchants_service.py` (or `tavern/application.py`) with one `haggle(...)` function: load or create through the TASK-0561 helper, negotiate, save, publish. The router maps the typed result to `HaggleResponse`.
3. Move `_check_session_auth` to `game_session/auth/`.
4. Delete the canned `get_merchant` payload. Not found gives 404. A store error gives 503.
5. No file over 500 lines.

## Frontdoor Blackbox Test Plan
- `GET /api/v1/merchants/{unknown}` returns 404.
- With a store double that raises on load, `GET` and `POST haggle` return 503 and save no events.
- A haggle on an existing merchant returns the same `HaggleResponse` and emits `HagglingNegotiated`. A haggle on a new merchant emits the creation event first.

## Definition of Done
- No `except Exception` and no canned payload remain in `routers/tavern.py`.
- No code outside `@handles` methods writes merchant aggregate state.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: high
- Source audits: `game-session.md (F2)`

## Orchestrator Addenda (2026-11-17, ownership)
- This task owns the tavern load sites that TASK-0561 did not cover:
  `services/game_session/src/game_session/routers/tavern.py:193-194`, `:246-247`, `:266-275` and
  `:313-322`. Not found gives 404. A store error gives 503. Delete the canned `Local Merchant`
  payload. Use the TASK-0561 load helpers. (TASK-0699 left these sites to this task.)
