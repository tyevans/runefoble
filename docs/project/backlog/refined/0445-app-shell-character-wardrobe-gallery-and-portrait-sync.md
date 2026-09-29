---
id: '0445'
title: App Shell Character Wardrobe Gallery Integration & Dynamic Condition Portrait Synchronization
status: Refined
created: 2026-09-29
dependencies:
- TASK-0124
- TASK-0255
- TASK-0444
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0006
- PRD-0016
- PRD-0023
governing_stories:
- US-0055
- US-0064
- US-0069
target_release: 0.9.0
---

# TASK-0445: App Shell Character Wardrobe Gallery Integration & Dynamic Condition Portrait Synchronization

## Status
Refined

## Summary
Integrate the `<runefoble-wardrobe-gallery>` component into the App Shell character sheet view (`frontend/src/runefoble-app.ts`), add wardrobe API communication methods to `frontend/src/services/app-data-service.ts`, bind `@select-variant` and `@generate-wardrobe` custom events, and synchronize active portrait updates across `<runefoble-character-card>`, pre-game lobby tokens, and the active VTT tactical board.

## Problem Statement
The `<runefoble-wardrobe-gallery>` component exists in `@runefoble/character-sheet-ui`, supporting visual attire variants, dynamic bloodied overlays (<50% HP), and condition indicators (poisoned, stunned, blinded). However, the component is not mounted within the App Shell character sheet route (`#/characters/:id`). As a result, players cannot inspect their character's wardrobe attire variants, generate new outfits (tavern casual, royal gala, arctic tundra), or set their active character portrait from the frontend application shell. Furthermore, changing portrait variants does not propagate to active game sessions or character cards.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/manage-generative-wardrobe-and-condition-portraits.md`: Synthesizing wardrobe variants and condition overlays.
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Character sheet navigation, equipment, and condition indicators.
  - `docs/reference/design-tokens-and-themes.md`: Bauhaus token styling for character cards and portrait frames.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Web Component encapsulation and custom event communication across Shadow DOM.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast portrait styling and condition status overlays.
  - **ADR-0013: Frontend Microfrontend Architecture**: Decoupled component mounting in the centralized App Shell.

## Product & User Story References
- [`prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md`](../../product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md)
- [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0055-dynamic-character-wardrobe-and-condition-portraits.md`](../../user_stories/accepted/us-0055-dynamic-character-wardrobe-and-condition-portraits.md)
- [`us-0069-deep-linkable-client-routing-and-route-guards.md`](../../user_stories/accepted/us-0069-deep-linkable-client-routing-and-route-guards.md)

## Detailed Specification & Implementation Plan
1. **App Data Service Extension (`frontend/src/services/app-data-service.ts`)**:
   - Add `fetchCharacterWardrobe(characterId: string): Promise<WardrobeVariant[]>` (< 30 lines).
   - Add `addWardrobeVariant(characterId: string, variant: NewWardrobeVariant): Promise<WardrobeVariant>` (< 30 lines).
   - Add `setCharacterPortrait(characterId: string, portraitUrl: string, variantId?: string): Promise<void>` (< 30 lines).
   - Update fallback fixtures with sample wardrobe attire variants for pre-seeded characters.
2. **App Shell Character Sheet View Composition (`frontend/src/runefoble-app.ts`)**:
   - Import `<runefoble-wardrobe-gallery>` and mount alongside `<runefoble-character-sheet>` and `<runefoble-stand-in-guardrails>` within a tabbed or side-by-side inspector layout (< 50 lines).
   - Handle `@select-variant` event: invoke `appDataService.setCharacterPortrait()` and update `activeCharacter.portraitUrl` in local state.
   - Handle `@generate-wardrobe` event: invoke `appDataService.addWardrobeVariant()` and show toast feedback.
3. **Cross-Component Synchronization**:
   - Verify that updating the character portrait automatically reflects in `<runefoble-character-card>`, the pre-game session lobby, and active VTT board token avatars.
4. **Verification**:
   - Add frontdoor tests in `frontend/test/wardrobe-gallery-integration.test.ts` asserting wardrobe gallery mounting, variant selection dispatch, and portrait synchronization.

## INVEST Criteria Evaluation
- **Independent (I)**: Mounts wardrobe gallery into the existing character sheet view via standard Lit events.
- **Negotiable (N)**: Layout placement (tabs vs accordion vs sidebar) can adapt to screen widths.
- **Valuable (V)**: Lets players customize and switch visual identities on their characters.
- **Estimable (E)**: Fits neatly alongside existing character sheet inspector subviews.
- **Small (S)**: Scope strictly isolated to client data service methods, App Shell event binding, and one test file.
- **Testable (T)**: Frontdoor Lit component testing verifying event dispatching and DOM updates.

## Definition of Done
1. `<runefoble-wardrobe-gallery>` mounted and functional in the character sheet view.
2. Players can view unlocked wardrobe variants and switch active portrait avatar.
3. Portrait updates synchronize immediately to character card and VTT token representations.
4. Frontdoor blackbox test suite `frontend/test/wardrobe-gallery-integration.test.ts` passes with 100% assertions.
5. All touched files adhere to Hard Invariant 6 (< 500 lines).
