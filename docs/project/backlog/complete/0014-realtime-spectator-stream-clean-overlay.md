---
id: 0014
title: Real-Time Spectator Stream & Chronicle Clean Overlay
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0004, TASK-0010, TASK-0012]
governing_adrs: [ADR-0001, ADR-0004, ADR-0006, ADR-0012]
target_release: 0.1.0
---

# TASK-0014 — Real-Time Spectator Stream & Chronicle Clean Overlay

## Status
Complete

## Summary
Implemented the dedicated clean-overlay spectator mode and streaming view for streamers and online viewers (US-0006, PRD-0005). Spectator mode streams live tactical board token movements, fog-of-war, dice rolls, and Watcher narrative chronicles over WebSockets while strictly redacting private DM tools, hidden tokens, and input controls. The frontend delivers a Bauhaus-styled `<runefoble-spectator-view>` web component optimized for OBS browser sources and live audience viewing.

## Scope & Key Changes
1. **Domain Events (`libs/runefoble_events/events.py`, `__init__.py`)**:
   - Defined and registered `SpectatorSessionConnected`: `session_id`, `viewer_id`, `viewer_name`, `connected_at` via `@register_event("runefoble.events.spectator.connected")`.
   - Exported in `__all__` across `events.py` and `__init__.py` with full CloudEvents 1.0 serialization and event registry support.
2. **Gateway Spectator API & Sanitization (`gateway/api/src/gateway_api/spectator.py`, `main.py`)**:
   - Added endpoint `GET /api/v1/spectate/{session_id}` accepting optional query parameter `token` or auth headers (`X-User-Id`, `Authorization`).
   - Implemented strict state sanitization in `spectator.py`:
     - Filters out hidden tokens (`hidden: True`, `is_secret: True`, `is_hidden: True`, `secret: True`).
     - Redacts monster stat blocks, HP, AC, and DM notes from tokens (only exposes id, name, position, conditions, cosmetic color, and AI flag).
     - Redacts root-level DM notes, private notes, and monster stat blocks.
     - Strips private entries from the narrative chronicle while preserving public speech and rulings.
     - Includes active scene atmosphere and sensory descriptions while cleansing secret lore.
   - Automatically dispatches `SpectatorSessionConnected` to the Redis bus (`runefoble.events.spectator` stream).
   - Gateway `main.py` kept strictly under 300 lines (Hard Invariant 6 <500 lines).
3. **Frontend Lit Web Component & Stories (`frontend/src/components/runefoble-spectator-view.ts`, `frontend/src/stories/spectator-view.stories.ts`)**:
   - Created Bauhaus-styled `<runefoble-spectator-view>` Lit component tailored for OBS overlays and spectator screens.
   - Read-only tactical board with tokens, conditions, and active-turn glowing indicators; user dragging and interaction disabled.
   - Bottom narrative chronicle ticker and ambient audio visualizer wave animation.
   - Transparent overlay mode support for OBS chroma/keying.
   - Created Storybook stories for `LiveEncounterStream` and `AtmosphericExploration`.
   - Exported in `frontend/src/index.ts` and registered in `frontend/src/runefoble-app.ts` with party/spectator mode toggle.
4. **Test Suite (`tests/test_spectator_view.py`)**:
   - Validated event registration, fields, and CloudEvents 1.0 compliance.
   - Validated state sanitization logic (hidden tokens, monster stat blocks, private notes stripped).
   - Validated FastAPI TestClient responses for default, token query param, and auth headers.
   - Validated Redis event bus dispatch of `SpectatorSessionConnected`.
5. **Documentation**:
   - Documented `SpectatorSessionConnected` in `docs/reference/events-schema.md`.
   - Updated backlog status in `docs/project/backlog/PRIORITY.md`.

## Verification
- `uv run pytest tests/test_spectator_view.py`: 8/8 passed.
- `uv run pytest`: 120/120 passed across monorepo.
- `uv run ruff check .`: Clean, 0 errors.
- `cd frontend && pnpm run build`: Clean TypeScript check and production bundle.
- File length limit: all files strictly under 500 lines.
