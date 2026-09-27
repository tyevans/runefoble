---
id: '0107'
title: Character Sheet UI Inventory Grid and Condition Indicator Microfrontend
status: Complete
created: 2026-09-26
dependencies:
- TASK-0009
- TASK-0018
- TASK-0077
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0006
governing_stories:
- US-0015
- US-0024
- US-0051
target_release: 0.4.0
pr_url: https://github.com/tyevans/runefoble/pull/107
---
# TASK-0107: Character Sheet UI Inventory Grid and Condition Indicator Microfrontend

## Status
Refined

## Summary
Develop the Lit Web Component microfrontend `<runefoble-character-sheet>` within `services/character_sheet/ui/` to visually display character attributes, equip/unequip gear in interactive slots (`main_hand`, `off_hand`, `armor`), inspect inventory encumbrance, and display active condition pills (both 5e/d20 rules and Runefoble absence penalties).

## Problem Statement
While `services/character_sheet` provides full event-sourced backend aggregates and REST endpoints (TASK-0009, TASK-0018, PRD-0006), players lack an encapsulated, responsive microfrontend to manage equipment, track spell slots, and inspect conditions visually. Providing `<runefoble-character-sheet>` fulfills US-0015, US-0024, and US-0051.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Packaging UI within `services/character_sheet/ui/`.
- **ADR-0004: Lit Web Components and Storybook UI**: Strict Shadow DOM encapsulation and Bauhaus geometric design tokens.
- **ADR-0007: API Gateway Architecture and Service Endpoints**: REST data binding against `/api/v1/characters/{id}`.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Service component boundary exposing `/ui/manifest`.

## Product & User Story References
- **Product Requirement**: [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)
- **User Stories**:
  - [`us-0015-character-inventory-equipment-tracking.md`](../../user_stories/accepted/us-0015-character-inventory-equipment-tracking.md)
  - [`us-0024-natural-speech-equipment-swapping-and-wake-word.md`](../../user_stories/accepted/us-0024-natural-speech-equipment-swapping-and-wake-word.md)
  - [`us-0051-character-level-progression-and-spellbook.md`](../../user_stories/accepted/us-0051-character-level-progression-and-spellbook.md)

## Detailed Specification & Implementation Plan
1. **Interactive Equipment & Inventory Grid**:
   - Visual paper doll slots for `main_hand`, `off_hand`, `armor`, and accessories with click-to-equip interactions.
   - Encumbrance capacity bar color-coded by load thresholds (Light, Medium, Heavy, Overburdened).
2. **Condition Indicators & Absence Badges**:
   - Distinct badges for tactical conditions (`blinded`, `prone`) and absence penalties (`drunk`, `foolishness`).
   - Interactive tooltip explaining mechanics and saving throw modifiers.
3. **Spellbook & Spell Slot Tracker**:
   - Visual slot tracker with clickable pips for expenditure and recovery.
4. **Storybook Stories & Manifest**:
   - Interactive Storybook stories for normal, encumbered, and heavily conditioned character states.
   - Vendored manifest in `services/character_sheet/ui/manifest.json` exposed at `/ui/manifest`.

## INVEST Criteria Evaluation
- **Independent (I)**: Decoupled presentation component consuming REST/WebSocket data via property bindings.
- **Negotiable (N)**: Paper doll layout vs grid list layout can be adapted.
- **Valuable (V)**: Gives players direct visual manipulation of inventory, spells, and statuses.
- **Estimable (E)**: Follows existing microfrontend patterns established across the workspace.
- **Small (S)**: Scope strictly isolated to `services/character_sheet/ui/`; all files < 200 lines.
- **Testable (T)**: Storybook visual verification and frontdoor blackbox test suite assertions.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Element**:
   - `<runefoble-character-sheet>` rendered with Shadow DOM encapsulation and Bauhaus tokens.
2. **Storybook Stories**:
   - Stories for healthy, encumbered, afflicted, and leveled-up character states with zero console errors.
3. **Microfrontend Manifest**:
   - Manifest served at `/ui/manifest` exposing tags, styles, and script entries per ADR-0013.
4. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_character_sheet_ui.py` validating component registration, manifest endpoint, and REST data binding.
5. **Quality Gates**:
   - Strictly conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `pnpm run build` and `uv run pytest tests/test_blackbox_character_sheet_ui.py`.
