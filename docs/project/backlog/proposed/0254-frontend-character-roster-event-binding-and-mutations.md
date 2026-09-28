---
id: '0254'
title: Frontend Character Roster Event Binding and Data Mutations
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0211
- TASK-0252
governing_adrs:
- ADR-0013
- ADR-0007
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
Proposed

## Summary
Wire event listeners in `frontend/src/runefoble-app.ts` for all actions dispatched by `<runefoble-character-roster>`: `@create-character`, `@assign-campaign`, `@delete-character`, and `@inspect-character`. Extend `AppDataService` (`frontend/src/services/app-data-service.ts`) with character mutation methods (`createCharacter`, `assignCharacterCampaign`, `deleteCharacter`) hitting `/api/v1/characters`.

## Problem Statement
The Character Roster component (`<runefoble-character-roster>`) provides rich user interactions (creating characters via modal, assigning them to campaigns, deleting characters, and inspecting sheets). However, in `runefoble-app.ts`, the component is rendered without any event listeners. When a user creates a character or assigns them to a campaign, the custom event is dropped silently, and no network request or state update occurs.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/develop-lit-components-in-storybook.md`: Custom event naming and Shadow DOM event dispatch.
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: Router navigation patterns.
- **Governing Architecture & ADRs**:
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
3. **Frontend Unit Tests (`frontend/test/character-roster.test.ts`)**:
   - Verify event dispatch and listener execution.

## Definition of Done
- [ ] Submitting the character builder modal saves character via Gateway API and updates the roster.
- [ ] Assigning a character to a campaign updates their campaign tag and persists to backend.
- [ ] Deleting a character removes them from the roster.
- [ ] Clicking "Inspect Sheet" navigates to `#/characters/:characterId`.
- [ ] Zero lint or typecheck errors; all files remain <500 lines.
