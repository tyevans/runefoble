---
id: '0609'
title: The Watcher Speech and Stand-In Routes Stop Sending Placeholder Ids and Report Provenance
status: Refined
created: 2026-11-17
dependencies:
- TASK-0607
governing_adrs:
- ADR-0002
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0001
- PRD-0002
governing_stories:
- US-0001
- US-0002
target_release: 0.9.0
severity: medium
source_audits:
- w1-the-watcher.md
- w2-inference-worker.md
---

# TASK-0609: The Watcher Speech and Stand-In Routes Stop Sending Placeholder Ids and Report Provenance

## Status
Refined

## Summary
The Watcher replaces missing campaign and session ids with the strings `current-campaign` and `current-session`. It also sends fixed scene data ("Dungeon chamber", "dark_fantasy") and does not send visible tokens on the speech path. Its speech result reports a default confidence of 0.9 and a template reply when the worker sends nothing. This task removes all placeholders, requires real ids, passes real scene data, and reports the source of each result.

## Problem Statement
- `routers/stand_in.py:36-37`: `req.campaign_id or "current-campaign"` and `req.session_id or "current-session"`.
- `routers/stand_in.py:40-41` and `autonomous_dm.py:101-106`: the same placeholders, plus "Dungeon chamber" and "dark_fantasy".
- `routers/intent/speech.py:39-48`: `visible_tokens` is not sent. The worker cannot resolve a target token on the cluster path.
- `speech.py:54`: default confidence 0.9. `speech.py:56-57`: fixed reply template.

Sources: `.audit/reports/w1-the-watcher.md` F10; `.audit/reports/w2-inference-worker.md` F13; `.audit/reports/w1-the-watcher.md` F4 (Watcher part).

## Documentation & Architecture Review
- `docs/explanation/the-watcher-autonomous-dm.md`: The Watcher supplies scene context.
- `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md` and `docs/how-to/manage-dm-copilot-whispers-and-veto-overrides.md`.
- TASK-0448 (proposed, provider router) also edits `speech.py`. Merge order: this task first, or coordinate.
- TASK-0607 defines the `source` field this task passes through.

## Product & User Story References
- `docs/project/product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md`
- `docs/project/product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md`
- `docs/project/user_stories/accepted/us-0003-dm-adjudicates-scene-with-ai-assistance.md`

## Detailed Specification & Implementation Plan
1. `StandInRequest` and the autonomous DM request make `campaign_id` and `session_id` required. Missing ids return 422.
2. Remove the literal scene defaults. Scene data comes from the request or from the board state route.
3. The speech path reads `visible_tokens` from the board state for the session and sends them to the worker.
4. Speech responses carry `source` from the worker. Remove the 0.9 default. If the worker reports no confidence, return `null`.
5. Remove the template reply. If the worker fails, return the error (see TASK-0607).

## Frontdoor Blackbox Test Plan
- Before fix: POST a stand-in request with no campaign id. The request succeeds with `current-campaign` (test fails).
- After fix: the same request returns 422.
- After fix: a speech request returns `confidence: null` when the worker omits it, and `source` from the worker.
- After fix: the worker receives the real `visible_tokens` for the session (checked through the worker's public request log or the test double at its HTTP boundary).

## Definition of Done
1. `current-campaign`, `current-session`, and "Dungeon chamber" are not in `services/the_watcher`.
2. Confidence default removed. Files under 500 lines.
3. Blackbox tests pass. Pytest for `services/the_watcher` passes.
4. Ruff check and format pass.
5. Event and endpoint docs updated.
