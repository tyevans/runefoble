---
id: '0673'
title: Campaign Lore Alias Conflicts Return 409 and Retrieval Wiring Fails Clearly
status: Complete
created: 2026-11-17
dependencies:
- TASK-0611
- TASK-0670
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds:
- PRD-0007
governing_stories:
- US-0036
target_release: 0.9.0
severity: medium
source_audits:
- work/0611.md
---

# TASK-0673: Campaign Lore Alias Conflicts Return 409 and Retrieval Wiring Fails Clearly

## Status
Complete

## Summary
Two defects in the campaign lore HTTP layer. A repeated alias merge raises a redstring domain error that no route maps, so the client gets HTTP 500. The retrieval engine dependency reads a field that exists only after the application lifespan has started, and it fails with a bare `AttributeError`.

## Problem Statement
- `services/campaign_lore/src/campaign_lore/routers/aliases.py` (`POST /api/v1/lore/aliases/consolidate`) calls `retrieval_engine.consolidate_alias`. `services/campaign_lore/src/campaign_lore/retrieval.py` calls the redstring consolidator. Redstring raises `DoubleMergeError` (and `MergeIntoAliasError`) when an entity is already merged. The route does not catch them. The result is HTTP 500.
- `services/campaign_lore/src/campaign_lore/dependencies.py:59-62` (`get_retrieval_engine`) reads `request.app.state.retrieval_engine`. When the app runs without its lifespan (for example, a test client without `with`), the read raises `AttributeError` with no useful message.

## Documentation & Architecture Review
- Redstring domain exceptions: `.venv/lib/python3.13/site-packages/redstring/domain/exceptions.py`. Confirm the exact class names before coding.
- ADR-0015: a conflict is a client error, not a server fault. A missing backend is a 503, not a 500.
- `docs/how-to/index-campaign-lore-with-redstring.md`: add the 409 response to the alias section.

## Product & User Story References
- PRD-0007 and US-0036: the DM links aliases to one canonical entity. A repeated link must report a conflict, not crash.

## Detailed Specification & Implementation Plan
1. In `routers/aliases.py`, catch `DoubleMergeError` and `MergeIntoAliasError` from the retrieval call. Raise `HTTPException(409, detail=...)` with the conflict reason. Do not call `document.consolidate_alias` after a conflict.
2. In `dependencies.py`, check that the lifespan set the engine. If it did not, raise a typed error from `runefoble_platform` that maps to HTTP 503 with the message "campaign_lore is not started".
3. Register the 409 and 503 responses in the route `responses=` argument so OpenAPI shows them.
4. Coordinate with TASK-0670 (same `retrieval.py` and `dependencies.py`). Merge 0670 first or rebase.

## Frontdoor Blackbox Test Plan
- Create a campaign and two documents through public lore routes. Consolidate alias "Mirela" to "Mirela Vance". Repeat the same call. The second call returns 409.
- `GET` the document after the 409. It lists one alias entry, not two.
- Build the app without lifespan and call the consolidate route through the public HTTP client. The response is 503 with the stated message, not 500.

## Definition of Done
- Tests above pass. No bare `except Exception` added.
- OpenAPI shows 409 and 503 for the consolidate route.
- `docs/how-to/index-campaign-lore-with-redstring.md` updated.
- `uv run pytest services/campaign_lore` and `make lint` pass.
