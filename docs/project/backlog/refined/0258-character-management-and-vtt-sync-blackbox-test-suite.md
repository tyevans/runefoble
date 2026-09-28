---
id: '0258'
title: Character Management and Tabletop Sync Blackbox Test Suite
status: Refined
created: 2026-09-27
dependencies:
- TASK-0252
- TASK-0254
- TASK-0255
- TASK-0256
- TASK-0257
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0004
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0006
- PRD-0023
governing_stories:
- US-0064
- US-0069
- US-0070
- US-0071
target_release: 0.8.0
---

# TASK-0258: Character Management and Tabletop Sync Blackbox Test Suite

## Status
Refined

## Summary
Implement a comprehensive end-to-end blackbox test suite (`tests/test_blackbox_character_management_and_vtt_sync.py` in Python and `frontend/test/character-management-and-profile.test.ts` in TypeScript) verifying the complete character lifecycle: creation via Gateway API, SpiceDB Zanzibar authorization checks, campaign assignment, character sheet route rendering (`#/characters/:id`), pre-game lobby selection sync, dynamic VTT card binding, profile settings view, and duplicate-free campaign creation.

## Problem Statement
While individual unit tests verify microfrontends in isolation, there is no end-to-end blackbox test suite verifying that characters created in the roster successfully link to campaigns, synchronize to the pre-game lobby, bind to active VTT sessions, and respect SpiceDB Zanzibar object authorization. Furthermore, tests are required to guard against regressions in event bubbling (double campaign creation) and profile view routing.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Frontdoor character testing workflows and condition management.
  - `docs/how-to/coordinate-game-session-lobby-and-readiness.md`: Lobby readiness and participant state assertions.
  - `docs/how-to/define-spicedb-zanzibar-permissions.md`: Writing Zanzibar relationship tuples and checking permissions.
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: Parameterized route assertions.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Frontdoor auth verification on character ownership and party membership.
  - **ADR-0002: Domain Events via eventsource-py**: Observable event assertions and projection validation.
  - **ADR-0004: Lit Web Components and Storybook UI**: Component mounting and DOM assertions.
  - **ADR-0010: Continuous Integration Pipeline**: Fast, reliable end-to-end blackbox tests.
  - **ADR-0013: Frontend Microfrontend Architecture**: Shell integration testing and event composition.

## Product & User Story References
- **Product Requirement**: [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md), [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Stories**:
  - [`us-0064-character-roster-management-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-management-and-party-assignment.md)
  - [`us-0069-character-sheet-inspector-and-active-session-binding.md`](../../user_stories/accepted/us-0069-character-sheet-inspector-and-active-session-binding.md)
  - [`us-0070-user-account-settings-and-profile-management.md`](../../user_stories/accepted/us-0070-user-account-settings-and-profile-management.md)
  - [`us-0071-campaign-dashboard-idempotency-and-lifecycle.md`](../../user_stories/accepted/us-0071-campaign-dashboard-idempotency-and-lifecycle.md)

## Detailed Specification & Implementation Plan
1. **Python Gateway & Zanzibar Blackbox Suite (`tests/test_blackbox_character_management_and_vtt_sync.py`)**:
   - `test_character_crud_and_zanzibar_ownership`: Create character via `POST /api/v1/characters`, assert owner tuple written in SpiceDB, assert non-owner cannot delete.
   - `test_character_campaign_assignment`: Assign character to campaign, assert campaign tuple written, assert party member can view character.
2. **Frontend Blackbox Integration Suite (`frontend/test/character-management-and-profile.test.ts`)**:
   - `test_roster_inspect_sheet_navigates_to_deep_route`: Click "Inspect Sheet", verify router navigates to `#/characters/:id` and mounts `<runefoble-character-sheet>`.
   - `test_campaign_creation_single_event_dispatch`: Submit campaign creator, assert exactly one `create-campaign` event is emitted and only one campaign is appended to dashboard.
   - `test_profile_route_renders_user_claims`: Navigate to `#/profile`, verify user claims and roles are displayed.
3. **Hard Invariant Invariants**:
   - All tests interact strictly through public frontdoor HTTP routes and DOM events.
   - Source files remain strictly <500 lines.

## INVEST Criteria Evaluation
- **Independent (I)**: Runs independently in pytest and frontend test runner.
- **Negotiable (N)**: Test assertions can focus on key frontdoor state mutations.
- **Valuable (V)**: Provides automated regression protection across character management and active VTT integration.
- **Estimable (E)**: Standard blackbox test suite sized within a single development pass.
- **Small (S)**: Test files split between Python API verification (< 300 lines) and frontend tests (< 300 lines).
- **Testable (T)**: Directly verifies observable HTTP outputs, DOM structures, and SpiceDB relations.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Python blackbox test suite `tests/test_blackbox_character_management_and_vtt_sync.py` implemented and passing.
2. Frontend integration test suite `frontend/test/character-management-and-profile.test.ts` implemented and passing.
3. Frontdoor setup is used exclusively without backdoor mock mutation.
4. All test files strictly adhere to file length limit (<500 lines).
