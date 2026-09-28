---
id: '0255'
title: Character Sheet Route and Inspector Subview Orchestration
status: Refined
created: 2026-09-27
dependencies:
- TASK-0206
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
- US-0066
- US-0069
target_release: 0.8.0
---

# TASK-0255: Character Sheet Route and Inspector Subview Orchestration

## Status
Refined

## Summary
Add the deep route `#/characters/:characterId` to the client-side router (`frontend/src/router/router.ts`) and create the `character-sheet` view in `frontend/src/runefoble-app.ts`. Mount the `<runefoble-character-sheet>` Web Component from `@runefoble/character-sheet-ui`, bind real character data loaded from `appDataService.fetchCharacter(characterId)`, and support breadcrumb navigation (`Home > Characters > [Character Name]`).

## Problem Statement
Although `<runefoble-character-sheet>` exists as a rich Lit component in `@runefoble/character-sheet-ui`, it is never imported or rendered anywhere in the `frontend` App Shell. When a user clicks "Inspect Sheet" on a character card in the roster, nothing happens. There is no route `#/characters/:characterId`, making it impossible to view or edit character inventory, equipped weapons, spell slots, condition badges, or AI stand-in policies.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Character sheet tabs, inventory encumbrance, and conditions.
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: Defining parameterized client routes and dynamic title resolvers.
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit component composition and theme token propagation.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Microfrontend composition into the App Shell.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain separation between gateway, character sheet, and shell.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast character inspector views.
  - **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend component composition and vendoring.

## Product & User Story References
- **Product Requirement**: [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md), [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Stories**:
  - [`us-0066-client-side-routing-navigation-and-breadcrumbs.md`](../../user_stories/accepted/us-0066-client-side-routing-navigation-and-breadcrumbs.md)
  - [`us-0069-character-sheet-inspector-and-active-session-binding.md`](../../user_stories/accepted/us-0069-character-sheet-inspector-and-active-session-binding.md)

## Detailed Specification & Implementation Plan
1. **Router Pattern (`frontend/src/router/router.ts`)**:
   - Register route `#/characters/:characterId` with breadcrumbs `[{ label: 'Home', path: '#/campaigns' }, { label: 'Characters', path: '#/characters' }, { label: 'Character Sheet', path: '#/characters/:characterId' }]`.
   - Update `router.setTitleResolver` for `character` type to resolve character names dynamically.
2. **App Shell View (`frontend/src/runefoble-app.ts`)**:
   - Add view type `'character-sheet'` to `AppActiveView`.
   - In `getActiveView()`, check `pat.startsWith('#/characters/') && pat !== '#/characters'`.
   - Import `@runefoble/character-sheet-ui`.
   - In `loadRouteData`, fetch character by ID via `appDataService.fetchCharacter(characterId)`.
   - In `renderActiveView`, render `<runefoble-character-sheet>` with character properties, equipped gear, and guardrails.
3. **Navigation Integration**:
   - Provide a "← Back to Roster" button in the character sheet header.
4. **Frontdoor Blackbox Verification (`tests/test_blackbox_character_sheet_route.py`)**:
   - Verify route resolution, dynamic breadcrumb title generation, and component mounting via frontdoors.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates within router and app shell view rendering pipeline.
- **Negotiable (N)**: Layout variants for mobile vs desktop can be adjusted.
- **Valuable (V)**: Unlocks full character sheet inspection from the roster, eliminating dead-end clicks.
- **Estimable (E)**: Pure Lit routing, view mounting, and data binding sized within a single pass.
- **Small (S)**: Kept under 120 lines of additions to `router.ts` and `runefoble-app.ts`.
- **Testable (T)**: Frontdoor component and router tests verify path matching and view transitions.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Navigating to `#/characters/:characterId` mounts `<runefoble-character-sheet>` with loaded character data.
2. Character vitals, stats, inventory, conditions, and spells display accurately.
3. Dynamic breadcrumb shows character name retrieved from character record.
4. "← Back to Roster" button navigates smoothly back to `#/characters`.
5. Blackbox frontdoor test suite passes via `uv run pytest tests/test_blackbox_character_sheet_route.py`.
6. All modified files strictly adhere to file length limit (<500 lines).
