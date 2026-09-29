---
id: '0515'
title: Establishment Detail Drawer and NPC Worker Assignment Component
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0260
- TASK-0514
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0024
governing_stories:
- US-0073
- US-0074
- US-0075
target_release: 0.9.0
---

# TASK-0515: Establishment Detail Drawer and NPC Worker Assignment Component

## Status
Proposed

## Summary
Implement `<runefoble-establishment-drawer>` Lit Web Component in `frontend/src/components/settlement/` to display establishment attributes, dynamic shelf vs. vault inventories, assignable living NPC workers with social relationship webs, and launch actions for merchant haggling and tavern minigames per PRD-0024.

## Problem Statement
While the domain aggregate for establishments and living NPC worker social graphs exists in the backend (`services/game_session/`), there is no UI component allowing players and DMs to inspect an individual establishment, view assigned workers (e.g. Head Baker, Master Armorer, Pit Boss), examine worker personalities and relationship webs (loyalty, debts, rivalries), inspect inventory wares, or trigger social interactions like merchant haggling or tavern minigames from the settlement view.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Slide-over drawer and modal dialogs with accessible keyboard traps.
- **ADR-0012: Theme Management and Bauhaus Design Tokens**: Bauhaus border radii, typography scale, and color tokens.
- **ADR-0013: Microfrontend Architecture & Modular Decomposition**: Isolated presentation component with event-driven external communication.

## Product & User Story References
- [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- [`us-0073-customizable-establishments-and-assignable-npc-workers.md`](../../user_stories/accepted/us-0073-customizable-establishments-and-assignable-npc-workers.md)
- [`us-0074-interactive-mobile-tavern-and-casino-minigames.md`](../../user_stories/accepted/us-0074-interactive-mobile-tavern-and-casino-minigames.md)
- [`us-0075-dynamic-merchant-haggling-with-dm-arbitration.md`](../../user_stories/accepted/us-0075-dynamic-merchant-haggling-with-dm-arbitration.md)

## Scope of Work
1. **Component Implementation (`frontend/src/components/settlement/runefoble-establishment-drawer.ts`)**:
   - Slide-over drawer supporting open/close transitions and escape key dismissal.
   - Header with establishment name, district badge, category icon, and prosperity tier.
   - Inventory tab/section: Dual-list view separating visible shelf inventory from locked vault inventory.
   - Workers tab/section: Assigned NPC cards displaying worker name, assigned role (Head Baker, Master Armorer, Pit Boss, Tavern Bouncer), Big Five quirks, and social relationship indicators (loyalty rating, debts, rivalries).
   - "Assign Worker" modal trigger for DMs to assign unassigned or newly hired town NPCs.
2. **Social Interaction Triggers**:
   - "Haggle with Merchant" action button dispatching `open-merchant-haggler` event with merchant NPC details.
   - "Enter Tavern Parlor" action button dispatching `open-tavern-minigames` event for hospitality establishments.
3. **Storybook Stories (`frontend/src/stories/runefoble-establishment-drawer.stories.ts`)**:
   - Author interactive Storybook stories showcasing commerce, hospitality, faith, and underworld establishment configurations.

## Definition of Done
1. `<runefoble-establishment-drawer>` is implemented with accessible slide-over interaction.
2. Displays inventory split (shelf vs vault) and NPC worker social relationship graphs.
3. Dispatches events to launch merchant haggling or minigames suites.
4. Storybook stories render without errors across all themes.
5. Code passes `pnpm test` and `pnpm lint`.
