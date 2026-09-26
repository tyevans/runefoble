---
id: 0022
title: Live Multi-User Turn Order, Initiative Tracker & Timer Web Component
status: Complete
created: 2026-09-25
completed: 2026-09-26
dependencies: [TASK-0010, TASK-0016, TASK-0017]
governing_adrs: [ADR-0004, ADR-0011, ADR-0012]
target_release: 0.1.0
---

# TASK-0022 — Live Multi-User Turn Order, Initiative Tracker & Timer Web Component

## Summary
Implemented real-time combat encounter initiative tracking, round advancement, and turn timer orchestration across `services/game_session`, `libs/runefoble_events`, and `frontend`. When combat starts, participants roll or submit initiative; the turn order is deterministically sorted (descending score with tiebreakers) and broadcast over WebSockets/REST. A Bauhaus-styled Lit component (`runefoble-initiative-tracker.ts`) visualizes active combatant, round count, countdown turn timer with urgent visual states, and next-in-line preview.

## Governing Architecture & ADRs
- **ADR-0004**: Lit Web Components and Storybook UI (Shadow DOM, reactive state).
- **ADR-0011**: Event Sourcing with `eventsource-py` (`InitiativeRolled`, `CombatEncounterStarted`, `InitiativeTurnAdvanced`, `CombatEncounterEnded`).
- **ADR-0012**: Bauhaus Modernist design tokens (cadmium red active badge, cobalt accents, hard geometric borders, monospaced timer).

## Definition of Done Verification
1. **Domain Events (`libs/runefoble_events/src/runefoble_events/session.py`)**:
   - `CombatEncounterStarted`: `session_id`, `round_number`, `combatants`.
   - `InitiativeRolled`: `session_id`, `combatant_id`, `combatant_name`, `initiative_score`, `is_npc`.
   - `InitiativeTurnAdvanced`: `session_id`, `round_number`, `active_combatant_id`, `turn_seconds_remaining`.
   - `CombatEncounterEnded`: `session_id`, `total_rounds`.
   - All events registered with `@register_event` and re-exported in `runefoble_events.events` and `runefoble_events.__init__`.
2. **GameSession Aggregate & Frontdoor API (`services/game_session`)**:
   - `POST /api/v1/sessions/{session_id}/combat/start`: Starts combat encounter.
   - `POST /api/v1/sessions/{session_id}/combat/initiative`: Submits combatant initiative roll/value.
   - `POST /api/v1/sessions/{session_id}/combat/next-turn`: Advances turn, cycling through sorted order and incrementing round on loop.
   - `POST /api/v1/sessions/{session_id}/combat/end`: Ends encounter.
   - `GET /api/v1/sessions/{session_id}/combat`: Returns current initiative state, round, current turn timer.
3. **Frontend Component & Storybook (`frontend/src/components/runefoble-initiative-tracker.ts`)**:
   - Interactive Lit component with Bauhaus typography, progress timer bar, active turn indicator, and skip/next turn controls.
   - Storybook story (`frontend/src/stories/runefoble-initiative-tracker.stories.ts`).
4. **Blackbox TDD Suite (`tests/test_blackbox_initiative_tracker.py`)**:
   - Strict frontdoor testing via `TestClient` exercising start combat -> submit initiative rolls -> advance turns across rounds -> end combat.
5. **File Invariant Check**:
   - All touched files remain strictly under 500 lines.
