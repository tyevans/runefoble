---
id: 0011
title: Absentee Session Chronicle and Audio Recap Engine
status: Complete
created: 2026-09-25
completed: 2026-09-25
dependencies: [TASK-0003, TASK-0006, TASK-0009]
governing_adrs: [ADR-0002, ADR-0004, ADR-0006, ADR-0007, ADR-0011]
target_release: 0.1.0
---

# TASK-0011 — Absentee Session Chronicle and Audio Recap Engine

## Status
Complete

## Summary
Implemented the session chronicle and absentee recap system (US-0005, PRD-0002). When an absent player returns for the next session, The Watcher aggregates the actions, penalty occurrences (e.g. drunk staggering, foolish blunders, greed lootings), damage taken, and loot acquired by their AI stand-in. The engine composes a humorous narrative chronicle, dispatches `AbsenteeRecapGenerated` over Redis Streams, and renders the chronicle in a dedicated Lit Web Component modal (`<runefoble-absentee-recap>`).

## Scope & Key Changes
1. **Domain Events (`libs/runefoble_events/events.py`, `__init__.py`)**:
   - Defined and registered `AbsenteeRecapGenerated` inheriting from `BaseRunefobleEvent` with `@register_event("runefoble.events.recap.generated")`.
   - Exposed in `__all__` with CloudEvents 1.0 serialization support.
2. **The Watcher Engine (`services/the_watcher/src/the_watcher/chronicle.py`, `main.py`, `models.py`)**:
   - Implemented `ChronicleRecapEngine.generate_recap(...)` producing persona-driven humorous narratives and penalty highlights ('drunk', 'foolishness', 'greed', 'cowardice').
   - Exposed `POST /api/v1/watcher/chronicle/recap` accepting `RecapRequest` and publishing `AbsenteeRecapGenerated` events.
   - Kept files under file length limits (Hard Invariant 6).
3. **Frontend Web Component & Storybook (`frontend/src/components/runefoble-absentee-recap.ts`, `frontend/src/stories/absentee-recap.stories.ts`)**:
   - Created `<runefoble-absentee-recap>` Lit component rendering chronicle details, styled penalty badges, and interactive audio play/pause controls.
   - Storybook stories for `DrunkCleric`, `FoolishRogue`, and `BattleReadyFighter`.
   - Exported in `frontend/src/index.ts` and imported in `frontend/src/runefoble-app.ts`.
4. **Verification & Tests (`tests/test_chronicle_recap.py`)**:
   - Unit tests for penalty mechanics ('drunk', 'foolishness', 'greed', and clean absence).
   - CloudEvents 1.0 and registry validation.
   - FastAPI TestClient integration test for `POST /api/v1/watcher/chronicle/recap`.

## Verification
- `uv run pytest`: 89/89 tests passed (including 7 new chronicle recap tests).
- `uv run ruff check .`: Clean, 0 errors.
- `cd frontend && pnpm run build`: Clean TypeScript check and production bundle.
- `cd frontend && pnpm run build-storybook`: Storybook build passed cleanly.
