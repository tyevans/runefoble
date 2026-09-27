---
id: '0215'
title: Campaign Management and Lobby Blackbox Test Suite
status: Complete
created: 2026-09-27
dependencies:
- TASK-0208
- TASK-0209
- TASK-0210
- TASK-0211
- TASK-0212
- TASK-0213
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0064
- US-0065
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/207
---
# TASK-0215: Campaign Management and Lobby Blackbox Test Suite

## Status
Refined

## Summary
Implement a blackbox frontdoor test suite verifying end-to-end campaign creation, player invitation, character party assignment, and pre-game session lobby launching into active VTT gameplay.

## Problem Statement
The transition from campaign creation to session lobby and active VTT involves multiple microservices (`gateway_api`, `game_session`, `character_sheet`) and SpiceDB Zanzibar authorization checks. A dedicated blackbox test suite is required to ensure reliable end-to-end execution.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/define-spicedb-zanzibar-permissions.md`: Verifying Zanzibar relationship tuples.
  - `docs/reference/ports-and-endpoints.md`: Public API routes for sessions and campaigns.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Verification of Zanzibar relation consistency.
  - **ADR-0004: Lit Web Components and Storybook UI**: UI integration standards.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Blackbox validation of microfrontend custom element events.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Story**: [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)
- **User Story**: [`us-0064-character-roster-management-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-management-and-party-assignment.md)
- **User Story**: [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)

## Detailed Specification & Implementation Plan
1. **Campaign Creation and Invite Flow Tests (`tests/test_blackbox_campaign_and_lobby.py`)**:
   - Verify creating a campaign via `POST /api/v1/campaigns` grants owner permissions in SpiceDB.
   - Verify invite link token generation and redemption via `POST /api/v1/campaigns/join`.
   - Verify role assignment updates Zanzibar tuples.
2. **Character Party Assignment Tests**:
   - Verify player creates a character and assigns it to a campaign party.
   - Verify character availability in the session lobby.
3. **Session Lobby Launch Transition Tests**:
   - Verify players joining lobby update presence and readiness indicators.
   - Verify DM triggering "Launch Session" fires `POST /api/v1/sessions/{id}/start` and emits `SessionStarted`.
   - Verify connected clients receive launch message and navigate to active session view.

## INVEST Criteria Evaluation
- **Independent (I)**: Runs as an automated Python pytest suite against public HTTP and event bus interfaces.
- **Negotiable (N)**: Assertions verify public state and published events without internal mocks.
- **Valuable (V)**: Protects the critical user journey from sign-up through live tabletop play.
- **Estimable (E)**: Standard FastAPI TestClient and event bus test pattern sized within one pass.
- **Small (S)**: Test module is strictly <350 lines, well below the 500-line invariant limit.
- **Testable (T)**: Executable via `uv run pytest tests/test_blackbox_campaign_and_lobby.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Test suite created in `tests/test_blackbox_campaign_and_lobby.py` (<350 lines).
2. Covers all acceptance criteria in US-0063, US-0064, and US-0065.
3. Tests execute with zero backdoor database or mock state injection.
4. Verified with `uv run pytest tests/test_blackbox_campaign_and_lobby.py`.
