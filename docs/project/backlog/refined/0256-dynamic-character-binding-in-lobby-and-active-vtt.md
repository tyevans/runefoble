---
id: '0256'
title: Dynamic Character Binding in Pre-Game Lobby and Active VTT
status: Refined
created: 2026-09-27
dependencies:
- TASK-0212
- TASK-0213
- TASK-0254
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0012
- ADR-0013
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
Refined

## Summary
Replace hardcoded character references in `frontend/src/runefoble-app.ts` with dynamically resolved character state. In `session-active`, bind `<runefoble-character-card>` to the character selected by the authenticated user during `session-lobby` staging (or the character assigned to the current campaign). Dynamically populate `availableCharacters` in `fetchLobbyState()` using the user's real character roster retrieved from `AppDataService`.

## Problem Statement
Currently, entering an active VTT session (`#/campaigns/:id/sessions/:sessionId`) renders `<runefoble-character-card>` hardcoded to "Kyra the Sun Maiden (Cleric Lvl 4, HP 28/32, AI Stand-in)" regardless of who is authenticated or which character was locked in during the pre-game lobby. Similarly, the lobby available character options are hardcoded fallbacks that do not reflect the user's actual created characters from the roster.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/coordinate-game-session-lobby-and-readiness.md`: Pre-game character selection, participant presence, and readiness.
  - `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md`: Passing character context from lobby to VTT during route transition.
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Character vitals, portrait rendering, and condition state.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Microfrontend encapsulation and event dispatching.
  - **ADR-0007: Domain-Driven Design Architecture**: Preserving bounded context separation between lobby staging and active board state.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast character card vitals rendering.
  - **ADR-0013: Frontend Microfrontend Architecture**: State composition across microfrontends via the App Shell.

## Product & User Story References
- **Product Requirement**: [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md), [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Stories**:
  - [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)
  - [`us-0069-character-sheet-inspector-and-active-session-binding.md`](../../user_stories/accepted/us-0069-character-sheet-inspector-and-active-session-binding.md)

## Detailed Specification & Implementation Plan
1. **Lobby State Character Resolution (`frontend/src/services/app-data-service.ts`)**:
   - In `fetchLobbyState(campaignId, sessionId)`, fetch the user's characters via `fetchCharacters()` and map them to `LobbyCharacterOption[]`.
   - Filter or prioritize characters assigned to the specified `campaignId`.
2. **App Shell State Binding (`frontend/src/runefoble-app.ts`)**:
   - Maintain `activeCharacter: CharacterItem | null` in `RunefobleApp` state.
   - On `@character-selected` from `<runefoble-session-lobby>`, store the selected character in session state.
   - When entering `session-active` route (`#/campaigns/:id/sessions/:sessionId`), resolve the active character (from selected state or fallback to first assigned character in campaign).
   - Pass dynamic character properties (`name`, `characterClass`, `level`, `currentHp`, `maxHp`, `armorClass`, `portraitUrl`) to `<runefoble-character-card>`.
   - If user is DM/owner, provide a character switcher or DM party inspector banner.
3. **Blackbox Frontdoor Verification (`tests/test_blackbox_lobby_and_vtt_character_sync.py`)**:
   - Verify character selected in lobby appears on VTT board card upon session launch.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates within the App Shell session state pipeline and lobby event listeners.
- **Negotiable (N)**: Fallback defaults when no character is selected can be customized.
- **Valuable (V)**: Eliminates hardcoded dummy characters from active VTT gameplay.
- **Estimable (E)**: Pure frontend state resolution and Lit binding sized for a single pass.
- **Small (S)**: Modest additions to `app-data-service.ts` and `runefoble-app.ts` under 120 lines.
- **Testable (T)**: Frontdoor component assertions verify rendered character name and vitals.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Pre-game lobby available characters reflect user's real character roster.
2. Character selected in pre-game lobby propagates to active VTT session card upon launch.
3. If no character was explicitly selected, defaults to campaign-assigned character or graceful placeholder.
4. Active VTT `<runefoble-character-card>` displays dynamic name, class, HP, AC, and portrait.
5. Blackbox frontdoor tests pass via `uv run pytest tests/test_blackbox_lobby_and_vtt_character_sync.py`.
6. All modified files strictly adhere to file length limit (<500 lines).
