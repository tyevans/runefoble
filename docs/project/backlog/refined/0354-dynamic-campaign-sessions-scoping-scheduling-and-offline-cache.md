---
id: '0354'
title: Dynamic Campaign Sessions Scoping, Scheduling & Offline Cache
status: Refined
created: 2026-09-28
dependencies:
- TASK-0250
- TASK-0251
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0065
target_release: 0.9.0
---

# TASK-0354: Dynamic Campaign Sessions Scoping, Scheduling & Offline Cache

## Status
Refined

## Summary
Eradicate hardcoded stub sessions by removing the universal "Session #15: Chamber of Horrors" fixture, scoping sessions strictly by campaign ID in `frontend/src/services/app-data-service.ts`, implementing an in-memory session cache that persists newly created sessions across view reloads in fallback mode, and auto-seeding an initial staging lobby session when a new campaign is created in `gateway_api/campaign_store/store.py`.

## Problem Statement
Every campaign opened in the application (including newly created campaigns) currently displays the exact same hardcoded "Session #15: Chamber of Horrors" alongside an active session. This occurs because `getFallbackCampaignSessions(campaignId)` in `app-data-service.fixtures.ts` hardcodes `{ id: 'lobby-${campaignId}-2', title: 'Session #15: Chamber of Horrors' }` for all campaigns. 

Furthermore, when a user clicks "+ Schedule Session" or creates a staging lobby in fallback/offline mode, `createCampaignSession()` returns an ephemeral object that is never stored. In `runefoble-app.ts:179`, `handleCreateSession` calls `fetchCampaignSessions(this.campaignId)` immediately afterward, which reads the original hardcoded array and wipes the newly created session from state. On the backend, `campaign_store/store.py` does not seed an initial staging lobby or session when a new campaign is created.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/coordinate-game-session-lobby-and-readiness.md`: Pre-game staging lobby assembly, session transitions, and participant presence.
  - `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md`: View staging transitions from campaign overview to lobby and active VTT.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Component presentation and modal integration.
  - **ADR-0007: Domain-Driven Design and Bounded Contexts**: Campaign and session lifecycle boundaries.
  - **ADR-0013: Frontend Microfrontend Architecture**: State synchronization between App Shell and game session components.

## Scope of Work & Implementation Plan
1. **Remove Hardcoded Universal Session Fixture (`frontend/src/services/app-data-service.fixtures.ts`)**:
   - Remove the static `Session #15: Chamber of Horrors` item from `getFallbackCampaignSessions()`.
   - Implement `FALLBACK_CAMPAIGN_SESSIONS_MAP: Record<string, CampaignSessionItem[]>`:
     - Campaign `'4'` (Tomb of the Star-Eater) has `Session #14: Tomb of the Star-Eater` (active) and `Session #15: Chamber of Horrors` (lobby).
     - Campaign `'5'` (Whispering Depths) has `Session #1: The Sunken Aqueduct` (upcoming).
     - New campaigns default to an initial `Session #1: Assembly & Briefing` (lobby).
2. **Session Persistence in Fallback Mode (`frontend/src/services/app-data-service.ts`)**:
   - Update `createCampaignSession()`:
     - When backend API request succeeds, return backend record.
     - When running in fallback mode, push newly created session into `FALLBACK_CAMPAIGN_SESSIONS_MAP[campaignId]`.
     - Ensure subsequent calls to `fetchCampaignSessions(campaignId)` include all created sessions.
3. **Backend Initial Session Seeding (`gateway/api/src/gateway_api/campaign_store/store.py`)**:
   - In `create_campaign()` / `create_from_request()`, automatically create a default staging lobby (`Session #1: Staging Lobby`, status: `lobby`) in `SessionManager`.
   - Write corresponding SpiceDB relation tuples `session:{id}#campaign@campaign:{campaign_id}`.
4. **Schedule Session Modal Enhancement (`frontend/src/components/runefoble-session-modal.ts`)**:
   - Ensure `scheduled_at` date/time and `description` fields are passed through to `handleCreateSession`.
   - Support creating either an immediate staging lobby or a scheduled upcoming session.
5. **Blackbox TDD Tests**:
   - Author `tests/test_blackbox_campaign_sessions_scoping.py` asserting that campaigns have isolated session lists and newly created sessions persist and appear upon listing.

## INVEST Criteria Evaluation
- **Independent (I)**: Focused specifically on campaign session scoping and creation without blocking other campaign tabs.
- **Negotiable (N)**: Initial session naming and status can be tuned based on DM preferences.
- **Valuable (V)**: Eliminates duplicate/confusing hardcoded sessions across campaigns and ensures created sessions persist.
- **Estimable (E)**: Clearly defined data structures and store operations.
- **Small (S)**: Confined to fixtures, app-data-service, and gateway store (< 120 lines altered).
- **Testable (T)**: Tested with frontdoor API requests and UI state assertions.

## Definition of Done
1. Newly created campaigns do not display "Session #15: Chamber of Horrors".
2. Creating a session via the UI or API persists across page navigation and list reloads.
3. Multiple campaigns exhibit independent, non-overlapping session rosters.
4. Backend `create_campaign` automatically seeds an initial staging lobby session with SpiceDB authorization.
5. All tests pass with zero regressions.
