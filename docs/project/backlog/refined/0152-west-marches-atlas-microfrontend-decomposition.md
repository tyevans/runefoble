---
id: '0152'
title: West Marches Shared Atlas Microfrontend Subviews and Pin Layer Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0127
- TASK-0135
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0018
governing_stories:
- US-0050
- US-0058
target_release: 0.5.0
---

# TASK-0152: West Marches Shared Atlas Microfrontend Subviews and Pin Layer Decomposition

## Status
Refined

## Summary
Decompose `services/campaign_lore/ui/src/runefoble-west-marches-atlas.ts` (386 lines, 77.2% of limit) into modular sub-components under `services/campaign_lore/ui/src/west_marches/` (`discovery_pin_layer.ts`, `stronghold_dashboard_panel.ts`, `frontier_hex_overlay.ts`), keeping all source files < 150 lines per Hard Invariant 6.

## Problem Statement
`runefoble-west-marches-atlas.ts` bundles frontier hex map navigation, party-specific discovery pin filtering, communal stronghold upgrade dashboards, and SpiceDB Zanzibar party isolation badges in one 386-line file. Decomposing these layers ensures clean separation of geographic rendering from settlement ledger logic.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Atomic custom element composition with Shadow DOM.
- **ADR-0012: Theming System and Accessibility Contrast Invariants**: Contrast styling for territorial markers.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Vendored in `services/campaign_lore/ui/`.

## Product & User Story References
- **Product Requirement**: [`prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md`](../../product/accepted/prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md)
- **User Story**: [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)

## Detailed Specification & Implementation Plan
1. **Discovery Pin Layer (`services/campaign_lore/ui/src/west_marches/pin_layer.ts`)**:
   - Milestone pin icons, party tag badges, and secret pin masking (< 130 lines).
2. **Stronghold Dashboard Panel (`services/campaign_lore/ui/src/west_marches/stronghold_panel.ts`)**:
   - Communal outpost treasury, defense tier readouts, and upgrade triggers (< 140 lines).
3. **Frontier Hex Overlay (`services/campaign_lore/ui/src/west_marches/hex_overlay.ts`)**:
   - Coordinate grid snapping and unexplored fog boundary layers (< 110 lines).
4. **Styles Decomposition (`services/campaign_lore/ui/src/west_marches/styles/`)**:
   - Split map view styles, pin badge styles, and panel styles (< 110 lines each).
5. **Atlas Root Element (`services/campaign_lore/ui/src/runefoble-west-marches-atlas.ts`)**:
   - Lightweight container managing viewport zoom, active party context, and sub-components (< 120 lines).
6. **Storybook Stories**:
   - Update `runefoble-west-marches-atlas.stories.ts` with sub-layer states.

## INVEST Criteria Evaluation
- **Independent (I)**: Frontend refactoring with zero modification to backend REST endpoints.
- **Negotiable (N)**: Panel placement can adjust based on screen width.
- **Valuable (V)**: Protects against file size invariant violations and improves atlas maintainability.
- **Estimable (E)**: Standard Lit component extraction and CSS modularization.
- **Small (S)**: Bounded strictly to `services/campaign_lore/ui/src/west_marches/`; all files < 150 lines.
- **Testable (T)**: Storybook stories verify visual rendering and frontdoor blackbox tests pass.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular UI Architecture**:
   - `services/campaign_lore/ui/src/west_marches/` created with focused sub-components.
   - All source and style files strictly < 180 lines.
2. **Storybook & Frontdoor Test Verification**:
   - Storybook stories render without console errors across Dark and Light themes.
   - Blackbox tests in `tests/test_blackbox_west_marches/` pass with zero regressions.
3. **Quality Gates**:
   - Passes `uv run ruff check .` and frontend build verification.
