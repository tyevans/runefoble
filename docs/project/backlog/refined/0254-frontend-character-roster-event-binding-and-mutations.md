---
id: '0254'
title: Frontend Character Roster Event Binding and Data Mutations
status: Refined
created: 2026-09-27
dependencies:
- TASK-0211
- TASK-0252
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0006
- PRD-0023
governing_stories:
- US-0064
- US-0069
target_release: 0.8.0
---

# TASK-0254: Frontend Character Roster Event Binding and Data Mutations

## Status
Refined

## Summary
Wire event listeners in `frontend/src/runefoble-app.ts` for all actions dispatched by `<runefoble-character-roster>`: `@create-character`, `@assign-campaign`, `@delete-character`, and `@inspect-character`. Extend `AppDataService` (`frontend/src/services/app-data-service.ts`) with character mutation methods (`createCharacter`, `assignCharacterCampaign`, `deleteCharacter`) hitting the Gateway `/api/v1/characters` endpoints.

## Problem Statement
The Character Roster component (`<runefoble-character-roster>`) provides rich user interactions (creating characters via modal, assigning them to campaigns, deleting characters, and inspecting sheets). However, in `runefoble-app.ts`, the component is rendered without any event listeners. When a user creates a character or assigns them to a campaign, the custom event is dropped silently, and no network request or state update occurs.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/develop-lit-components-in-storybook.md`: Custom event naming and Shadow DOM event dispatch.
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: Router navigation patterns.
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Character attributes, inventory, and stats.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Ensuring character creation and campaign assignment check permissions.
  - **ADR-0004: Lit Web Components and Storybook UI**: Microfrontend event composition into the App Shell.
  - **ADR-0007: Domain-Driven Design Architecture**: Gateway orchestrating character sheet and campaign boundaries.
  - **ADR-0013: Frontend Microfrontend Architecture**: Lit Web Components emitting standard DOM events.

## Product & User Story References
- **Product Requirement**: [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md), [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Stories**:
  - [`us-0064-character-roster-management-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-management-and-party-assignment.md)
  - [`us-0069-character-sheet-inspector-and-active-session-binding.md`](../../user_stories/accepted/us-0069-character-sheet-inspector-and-active-session-binding.md)

## Detailed Specification & Implementation Plan
1. **AppDataService Character Mutations (`frontend/src/services/app-data-service.ts`)**:
   - `createCharacter(payload: CreateCharacterPayload): Promise<CharacterItem>`: POST to `/api/v1/characters`.
   - `assignCharacterCampaign(characterId: string, campaignId: string | null): Promise<void>`: PATCH to `/api/v1/characters/{id}/campaign`.
   - `deleteCharacter(characterId: string): Promise<void>`: DELETE to `/api/v1/characters/{id}`.
2. **App Shell Event Handlers (`frontend/src/runefoble-app.ts`)**:
   - Add `@create-character`: Call `appDataService.createCharacter`, re-fetch characters, display toast notification.
   - Add `@assign-campaign`: Call `appDataService.assignCharacterCampaign`, update local character list.
   - Add `@delete-character`: Call `appDataService.deleteCharacter`, remove from local character list.
   - Add `@inspect-character`: Execute `router.navigate('#/characters/' + e.detail.characterId)`.
3. **Frontdoor Blackbox Verification (`tests/test_blackbox_character_roster_binding.py`)**:
   - Verify frontdoor event emission and router transition contracts.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates between roster web component and gateway character API.
- **Negotiable (N)**: Optimistic client updates vs server re-fetching can be tuned.
- **Valuable (V)**: Bridges interactive UI elements to backend persistence, turning visual roster into functional system.
- **Estimable (E)**: Pure Lit event handler wiring and fetch client methods sized within a single pass.
- **Small (S)**: Kept under 150 lines of additions to `runefoble-app.ts` and `app-data-service.ts`.
- **Testable (T)**: Frontdoor component tests verify event propagation and REST API mutation calls.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Submitting the character builder modal emits `@create-character`, calls Gateway API, and updates the roster.
2. Assigning a character to a campaign emits `@assign-campaign`, updates campaign tag, and persists to backend.
3. Deleting a character emits `@delete-character`, calls DELETE `/api/v1/characters/{id}`, and removes item from roster.
4. Clicking "Inspect Sheet" emits `@inspect-character` and navigates router to `#/characters/:characterId`.
5. Blackbox frontdoor tests in `tests/test_blackbox_character_roster_binding.py` pass.
6. Zero lint or typecheck errors; all modified files remain <500 lines.
