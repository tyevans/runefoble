---
id: '0356'
title: Character Sheet Sub-Resource Mutations & Event-Sourced Persistence Integration
status: Complete
created: 2026-09-28
dependencies:
- TASK-0009
- TASK-0018
- TASK-0248
governing_adrs:
- ADR-0002
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0004
- PRD-0023
governing_stories:
- US-0007
- US-0066
target_release: 0.9.0
pr_url: https://github.com/tyevans/runefoble/pull/350
---
# TASK-0356: Character Sheet Sub-Resource Mutations & Event-Sourced Persistence Integration

## Status
Refined

## Summary
Bridge the architectural disconnect between the Lit character sheet microfrontend and the backend `character_sheet:8003` microservice by reverse-proxying character sub-resource endpoints on `gateway-api`, adding character mutation methods to `frontend/src/services/app-data-service.ts`, binding all 11 action event listeners on `<runefoble-character-sheet>` in `frontend/src/runefoble-app.ts`, and adding interactive HP adjustment controls in `stats.template.ts`.

## Problem Statement
While high-level character CRUD (creation, deletion, campaign assignment, inspection) is wired through `gateway-api`, all sub-resource mutations on the Character Sheet are completely disconnected from backend persistence:
1. `<runefoble-character-sheet>` dispatches 11 action events (`hp-change`, `equip-item`, `unequip-item`, `add-item`, `remove-item`, `cast-spell`, `prepare-spell`, `apply-condition`, `remove-condition`, `expend-slot`, `restore-slot`), but `runefoble-app.ts:222-227` attaches zero listeners to them. Any equipment changes, inventory additions, condition updates, or spell expenditures made by the user are lost upon navigation or refresh.
2. In `services/character_sheet/ui/src/templates/stats.template.ts`, HP is a display-only text string; the method `handleHpDelta(delta)` exists in `runefoble-character-sheet.ts:91` but is orphaned with no buttons or controls invoking it.
3. In `templates/spells.template.ts:50`, the Cast button hardcodes slot tier 1 (`handleCastSpell(spell, 1)`) regardless of the spell's actual level.
4. The `character_sheet` microservice (port 8003) contains a rich `eventsource-py` aggregate and FastAPI router for health, inventory, equipment, spells, and conditions, but `gateway-api` does not reverse-proxy these endpoints, relying instead on a stripped-down in-memory `CharacterStore`.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/define-event-sourced-aggregates.md`: Defining declarative aggregates and handling domain events with `eventsource-py`.
  - `docs/how-to/interact-with-character-sheet-and-inventory.md`: Character equipment slots, inventory encumbrance, condition tags, and spell tracking.
- **Governing Architecture & ADRs**:
  - **ADR-0002: Event Sourcing and CQRS with eventsource-py**: Domain state transitions via aggregates.
  - **ADR-0004: Lit Web Components and Storybook UI**: Presentation isolation in web components.
  - **ADR-0007: Domain-Driven Design and Bounded Contexts**: Character Sheet bounded context boundaries.
  - **ADR-0013: Frontend Microfrontend Architecture**: Event bubbling from microfrontends into App Shell.

## Scope of Work & Implementation Plan
1. **Gateway Character Sub-Resource Routing (`gateway/api/src/gateway_api/routers/characters.py`)**:
   - Proxy or implement routes for:
     - `POST /api/v1/characters/{id}/health`: Mutates character HP, checks stand-in stabilization.
     - `POST /api/v1/characters/{id}/equipment`: Equips item to designated slot.
     - `DELETE /api/v1/characters/{id}/equipment/{slot}`: Unequips item.
     - `POST /api/v1/characters/{id}/inventory`: Adds item to inventory.
     - `DELETE /api/v1/characters/{id}/inventory/{item_id}`: Removes item.
     - `POST /api/v1/characters/{id}/conditions` & `DELETE /api/v1/characters/{id}/conditions/{condition}`: Adds/removes conditions.
     - `POST /api/v1/characters/{id}/spells/cast` & `POST /api/v1/characters/{id}/spells/prepare`: Casts/prepares spells.
   - Enforce Zanzibar `edit` permission on all mutators.
2. **App Data Service Character Mutations (`frontend/src/services/app-data-service.ts`)**:
   - Implement `modifyCharacterHealth(characterId, delta, source)`.
   - Implement `equipCharacterItem(characterId, slot, itemName)`.
   - Implement `unequipCharacterItem(characterId, slot)`.
   - Implement `addCharacterInventoryItem(characterId, item)`.
   - Implement `removeCharacterInventoryItem(characterId, itemId, quantity)`.
   - Implement `applyCharacterCondition(characterId, condition, source)`.
   - Implement `removeCharacterCondition(characterId, condition)`.
   - Implement `castCharacterSpell(characterId, spellName, slotLevel)`.
   - Implement `prepareCharacterSpell(characterId, spellName, isPrepared)`.
   - Provide fallback cache mutations so offline/storybook development continues to function.
3. **App Shell Event Listeners (`frontend/src/runefoble-app.ts`)**:
   - Bind all 11 action event listeners on `<runefoble-character-sheet>`:
     - `@hp-change`, `@equip-item`, `@unequip-item`, `@add-item`, `@remove-item`, `@cast-spell`, `@prepare-spell`, `@apply-condition`, `@remove-condition`, `@expend-slot`, `@restore-slot`.
   - Perform optimistic UI state updates and persist via `appDataService`.
   - Display toast confirmations (e.g., `Equipped Longsword`, `Condition Poisoned removed`).
4. **Template Interactive Improvements**:
   - In `services/character_sheet/ui/src/templates/stats.template.ts`, add quick HP delta buttons (`-5`, `-1`, `+1`, `+5`) that invoke `sheet.handleHpDelta(delta)`.
   - In `services/character_sheet/ui/src/templates/spells.template.ts`, pass `spell.level` to `handleCastSpell` instead of hardcoded `1`.
   - In `services/character_sheet/ui/src/templates/inventory.template.ts`, provide slot selector dialog when equipping.
5. **Blackbox TDD Tests**:
   - Author `tests/test_blackbox_character_sheet_mutations.py` asserting frontdoor HTTP mutation calls and state persistence.
   - Update `frontend/test/character-management-and-profile.test.ts`.

## INVEST Criteria Evaluation
- **Independent (I)**: Targets character sheet sub-resource management independently of lobby or campaign views.
- **Negotiable (N)**: HP step buttons and slot selection UI can be tuned.
- **Valuable (V)**: Transforms the Character Sheet from a passive, ephemeral mockup into a fully interactive, persistent character sheet.
- **Estimable (E)**: Event contracts and backend endpoints are already defined and documented.
- **Small (S)**: Focused on event bindings in App Shell, service methods, and template controls (< 150 lines per module).
- **Testable (T)**: Tested with frontdoor HTTP requests and Lit element event dispatch assertions.

## Definition of Done
1. Modifying HP, equipping an item, adding loot, or casting a spell persists to the backend or fallback cache.
2. Navigating away from a character sheet and returning preserves all equipment, inventory, and condition modifications.
3. Interactive HP buttons exist and function in `stats.template.ts`.
4. All 11 character sheet events are caught and handled in `runefoble-app.ts`.
5. Tests pass 100% with no regressions.
