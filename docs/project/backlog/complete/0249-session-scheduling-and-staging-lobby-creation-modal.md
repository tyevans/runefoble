---
id: 0249
title: Session Scheduling and Staging Lobby Creation Modal
status: Complete
created: 2026-09-27
dependencies:
- TASK-0246
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0007
- ADR-0012
governing_prds:
- PRD-0023
governing_stories:
- US-0065
- US-0067
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/283
---
# TASK-0249: Session Scheduling and Staging Lobby Creation Modal

## Status
Refined

## Summary
Enhance `runefoble-session-list` in `frontend/src/components/runefoble-session-list.ts` with a modal dialog for scheduling upcoming sessions or immediately launching a pre-game staging lobby, connecting directly to the Gateway API's `POST /api/v1/campaigns/{campaign_id}/sessions` endpoint.

## Problem Statement
Clicking "+ New Session" currently triggers a direct navigation to `#/campaigns/:id/lobby/new`, treating the literal string `"new"` as an active session ID. Because no session entity is created in the backend, the pre-game lobby fails to load real participants or persist readiness. Game Masters have no way to name upcoming sessions, specify dates, or add scenario briefing notes.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/coordinate-game-session-lobby-and-readiness.md`: Pre-game assembly and session lifecycle.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Form controls and modals in Lit Web Components.
  - `docs/reference/ports-and-endpoints.md`: Gateway routing table and session endpoints.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Enforcing `run_session` permission to trigger session creation.
  - **ADR-0004: Lit Web Components and Storybook UI**: Shadow DOM modal patterns.
  - **ADR-0007: Domain-Driven Design Architecture**: Gateway session management boundary.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast input elements and buttons.

## Product & User Story References
- **Product Requirement**: [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Story**: [`us-0067-campaign-detail-view-and-session-scheduling.md`](../../user_stories/accepted/us-0067-campaign-detail-view-and-session-scheduling.md)

## Detailed Specification & Implementation Plan
1. **Modal Form Component (`frontend/src/components/runefoble-session-modal.ts`)**:
   - Fields: Session Title (e.g. "Chapter 4: The Sunken Vault"), Scheduled Date/Time picker, Description / DM Notes, Initial Status selection ("lobby" vs "upcoming").
   - Action buttons: "Cancel" and "Create Session" with validation states.
2. **Event Dispatch & Service Binding**:
   - Dispatch custom event `@create-session` with detail: `{ title, scheduledAt, description, status }`.
   - In `app-data-service.ts`, call `POST /api/v1/campaigns/{campaign_id}/sessions`.
   - On success, refresh campaign sessions and route to `#/campaigns/:id/lobby/:sessionId` if status was "lobby".
3. **Storybook Stories (`frontend/src/stories/runefoble-session-modal.stories.ts`)**:
   - Add Storybook scenarios demonstrating open modal state, form submission, validation errors, and dark/light mode rendering.
4. **Frontdoor Blackbox Verification (`tests/test_blackbox_session_modal.py`)**:
   - Verify modal markup, event signatures, and gateway integration contract via frontdoors.

## INVEST Criteria Evaluation
- **Independent (I)**: Decoupled modal component interacting via standard DOM events and gateway REST API.
- **Negotiable (N)**: Advanced scheduling options (calendar sync, reminder notifications) deferred to future tasks.
- **Valuable (V)**: Eliminates broken navigation to fake `/lobby/new` and enables real session lifecycle orchestration.
- **Estimable (E)**: Pure Lit Web Component modal and event wiring sized for a single pass.
- **Small (S)**: Kept under 200 lines to adhere to file length invariants.
- **Testable (T)**: Frontdoor component and API contract tests verify form input validation and event payload emission.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Session creation modal opens when clicking "+ New Session" in `runefoble-session-list`.
2. Submitting the form emits `@create-session` with valid payload and closes modal.
3. Successful creation persists session via Gateway API and updates session list.
4. Storybook stories pass in all color modes (Dark/Light/System).
5. Frontdoor test suite passes via `uv run pytest tests/test_blackbox_session_modal.py`.
6. All source files strictly adhere to file length limit (<500 lines).
