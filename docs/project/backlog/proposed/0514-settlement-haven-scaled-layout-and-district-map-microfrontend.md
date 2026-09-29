---
id: '0514'
title: Settlement Haven Scaled Layout and District Map Microfrontend
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0259
- TASK-0513
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0072
- US-0073
target_release: 0.9.0
---

# TASK-0514: Settlement Haven Scaled Layout and District Map Microfrontend

## Status
Proposed

## Summary
Implement `<runefoble-settlement-haven>` Lit Web Component in `frontend/src/components/settlement/` with high-contrast Bauhaus design tokens, interactive district zoning, settlement scaling across five tiers (Hamlet/Thorp to Grand Metropolis), and mobile-first touch optimization per PRD-0024 and US-0072.

## Problem Statement
Per PRD-0024 Checkable Outcome 1, players navigating to `#/campaigns/:id/town` on a mobile smartphone viewport must experience a fluid, touch-optimized UI with sub-100ms response time and zero layout clipping. Currently, there is no UI component presenting the geographic layout, district zoning (Hospitality, Commerce, Civic, Faith, Underworld), settlement scale indicators, or clickable establishment map nodes.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated web component with isolated styles.
- **ADR-0012: Theme Management and Bauhaus Design Tokens**: Bauhaus geometry, contrast invariants, and typography tokens.
- **ADR-0013: Microfrontend Architecture & Modular Decomposition**: Shadow DOM presentation boundary.

## Product & User Story References
- [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- [`us-0072-mobile-responsive-settlement-browser-and-town-builder.md`](../../user_stories/accepted/us-0072-mobile-responsive-settlement-browser-and-town-builder.md)
- [`us-0073-customizable-establishments-and-assignable-npc-workers.md`](../../user_stories/accepted/us-0073-customizable-establishments-and-assignable-npc-workers.md)

## Scope of Work
1. **Component Scaffolding (`frontend/src/components/settlement/runefoble-settlement-haven.ts`)**:
   - Render settlement header: Haven name, population tier badge, prosperity score, and defense rating.
   - Five distinct settlement scale layouts:
     - Hamlet / Thorp (Pop: 20–150): Ribbon or cluster layout, communal well, wayside inn/smithy.
     - Village / Frontier Haven (Pop: 150–1,000): Radial green layout, timber palisade, bakery, chapel, general trading post.
     - Market Town (Pop: 1,000–6,000): Walled perimeter, paved marketplace, artisan quarters, guildhalls, town watch barracks.
     - Fortified City (Pop: 6,000–25,000): Multi-ring defensive walls, segregated districts, coliseum, gambling halls.
     - Grand Metropolis (Pop: 25,000–100,000+): Sprawling quarters, monumental architecture, high-roller gilded casinos.
2. **Interactive District Map & Nodes**:
   - District filter chips: Hospitality, Commerce, Civic, Faith, Underworld.
   - Interactive establishment cards/nodes displaying name, category icon, active workers count, and status badge.
   - Dispatch `select-establishment` event with establishment details upon tap/click.
3. **Responsive Mobile Optimization**:
   - Touch-optimized scrolling and grid layouts ensuring zero horizontal clipping on 360px–420px mobile viewports.
4. **Storybook Stories (`frontend/src/stories/runefoble-settlement-haven.stories.ts`)**:
   - Author comprehensive stories covering all five settlement scale tiers, district filters, and empty/busy states across themes.

## Definition of Done
1. `<runefoble-settlement-haven>` is implemented and exports cleanly.
2. Renders all five settlement scale tiers with corresponding district categorizations.
3. Dispatches `select-establishment` and `create-establishment` custom events.
4. Storybook stories exist and render with zero console warnings in dark, light, and high-contrast modes.
5. Passes `pnpm test` and `pnpm lint`.
