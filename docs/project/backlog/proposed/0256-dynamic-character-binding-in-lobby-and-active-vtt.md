---
id: '0256'
title: Dynamic Character Binding in Pre-Game Lobby and Active VTT
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0212
- TASK-0213
- TASK-0254
governing_adrs:
- ADR-0013
- ADR-0007
governing_prds:
- PRD-0006
- PRD-0023
governing_stories:
- US-0065
- US-0069
target_release: 0.8.0
---
# TASK-0256: Dynamic Character Binding in Pre-Game Lobby and Active VTT

## Status
Proposed

## Summary
Replace hardcoded character references in `frontend/src/runefoble-app.ts` with dynamically resolved character state. In `session-active`, bind `<runefoble-character-card>` to the character chosen by the current user in `session-lobby` (or the character assigned to the current campaign). Dynamically populate `availableCharacters` in `fetchLobbyState` using the authenticated user's real character roster.

## Problem Statement
Currently, entering an active VTT session (`#/campaigns/:id/sessions/:sessionId`) always renders `<runefoble-character-card>` hardcoded to "Kyra the Sun Maiden (Cleric Lvl 4, HP 28/32, AI Stand-in)" regardless of who is playing or what character was selected in the lobby. Similarly, the lobby available character options are hardcoded fallbacks that do not reflect the user's actual created characters.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/coordinate-game-session-lobby-and-readiness.md`: Pre-game character selection and participant lock-in.
  - `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md`: Passing character context from lobby to VTT.
- **Governing Architecture & ADRs**:
  - **ADR-0013: Frontend Microfrontend Architecture**: Data flow and state composition between shell and components.

## Product & User Story References
- **Product Requirement**: [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md), [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Stories**:
  - [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)
  - [`us-0069-character-sheet-inspector-and-active-session-binding.md`](../../user_stories/accepted/us-0069-character-sheet-inspector-and-active-session-binding.md)

## Detailed Specification & Implementation Plan
1. **Lobby State Character Resolution (`frontend/src/services/app-data-service.ts`)**:
   - In `fetchLobbyState()`, populate `availableCharacters` with the user's characters from `fetchCharacters()`.
2. **App Shell State Binding (`frontend/src/runefoble-app.ts`)**:
   - Maintain `activeCharacter: CharacterItem | null` on `RunefobleApp`.
   - On `@character-selected` in the lobby, store the chosen character in session storage and component state.
   - When rendering `session-active`, pass the active character's name, class, HP, max HP, and stand-in status to `<runefoble-character-card>`.
   - If the player is a DM, display party character switcher or DM inspector card.

## Definition of Done
- [ ] Active VTT character card reflects the user's selected character, not a static hardcoded dummy.
- [ ] Lobby available characters reflect user's real character roster.
- [ ] Transition from lobby to session preserves character binding.
- [ ] All unit tests pass and file length remains <500 lines.
