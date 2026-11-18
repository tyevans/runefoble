---
id: '0617'
title: Board State Get Returns 404 for Unknown Boards and Never Seeds Fake Tokens
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0007
- ADR-0011
- ADR-0014
governing_prds:
- PRD-0005
governing_stories:
- US-0014
target_release: 0.9.0
---

# TASK-0617: Board State Get Returns 404 for Unknown Boards and Never Seeds Fake Tokens

## Status
Complete

## Summary
`get_or_create_board` creates and saves a board with the tokens "Valeros", "Kyra" and "Goblin Scout" for any unknown id. It also catches every load exception, so a store outage can overwrite a real board with the seeded one. This task makes GET return 404 for unknown boards, makes only POST create a board, and lets load errors propagate.

## Problem Statement
- `services/board_state/src/board_state/dependencies.py` `get_or_create_board` catches `Exception` from `repo.load`.
- It then creates a 12x12 board with hard-coded tokens and calls `repo.save`.
- A GET on any new session id writes this state.
- A store outage can overwrite an existing board.

Source: `.audit/reports/w1-board-state.md` F5.

## Documentation & Architecture Review
- `docs/reference/ports-and-endpoints.md` and the board routes reference: document 404 for GET of unknown boards.
- `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`: check any flow that relies on GET creating a board. Update it to POST first.
- ADR-0011: state changes go through aggregates. Creation must be an explicit command.
- Note: the gateway board routes may rely on GET creating boards. Check `gateway/api` callers and the App Shell (see w2-app-shell F2). Coordinate.

## Product & User Story References
- `docs/project/product/accepted/prd-0005-realtime-websocket-board-sync.md`
- `docs/project/user_stories/accepted/us-0014-realtime-board-websocket-sync.md`

## Detailed Specification & Implementation Plan
1. Remove `get_or_create_board`. Replace with `get_board` that raises 404 when the aggregate does not exist.
2. Keep creation in the `POST /api/v1/boards` handler only.
3. Remove the `except Exception` around `repo.load`. Let storage errors become 5xx.
4. Remove the hard-coded seed tokens from production code. A fixture may create a board through POST in tests.
5. Update callers that relied on GET creation to call POST first.

## Frontdoor Blackbox Test Plan
- Before fix: GET `/api/v1/boards/<new-id>` returns 200 with tokens "Valeros", "Kyra" (test fails).
- After fix: the same GET returns 404 and publishes no event.
- After fix: POST then GET returns the board the caller created, with no extra tokens.
- After fix: with the store forced to fail on load (test double at the store port), GET returns 5xx and the stored board is not changed.

## Definition of Done
1. No token literals "Valeros", "Kyra", "Goblin Scout" in `services/board_state/src`.
2. Files under 500 lines.
3. Blackbox tests pass. `uv run pytest services/board_state` passes.
4. Ruff check and format pass.
5. Board routes reference and how-to updated. `CHANGELOG.md` `[Unreleased]` entry added.

## Audit Provenance

- Severity: high
- Source audits: `w1-board-state.md`
