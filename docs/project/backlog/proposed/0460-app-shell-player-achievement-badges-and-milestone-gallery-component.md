---
id: '0460'
title: App Shell Player Achievement Badges and Milestone Gallery Component
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0110
- TASK-0458
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0012
- PRD-0023
governing_stories:
- US-0040
- US-0054
- US-0067
target_release: 0.9.0
---

# TASK-0460: App Shell Player Achievement Badges and Milestone Gallery Component

## Status
Proposed

## Summary
Develop the Lit Web Component `<runefoble-achievement-gallery>` within `services/campaign_analytics/ui` and integrate it as a dedicated tab within `<runefoble-campaign-analytics>` and the App Shell Campaign Hub. Render unlocked player achievement badges, in-progress milestone meters, rarity tiers (Common, Rare, Epic, Legendary), and category filters with Bauhaus geometric styling and theme contrast invariants.

## Problem Statement
While PRD-0012 calls for players and absent participants to review unlocked achievements and milestone badges, `<runefoble-campaign-analytics>` only provides subviews for spatial heatmaps, MVP performance charts, and the chronicle timeline. Without a dedicated achievement gallery component, players cannot view their accumulated campaign achievements, track progress towards incomplete milestones (e.g. 74/100 Goblins), or celebrate rare milestones with party members.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Strict Shadow DOM encapsulation and reactive property bindings.
- **ADR-0012: Design Tokens and Bauhaus Modernist Theme**: Bauhaus geometric badge borders, rarity color variables, and high-contrast dark/light mode tokens.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Service microfrontend boundary exposed via `/ui/manifest`.

## Product & User Story References
- [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0040-campaign-combat-telemetry-and-living-timeline.md`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)
- [`us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md`](../../user_stories/accepted/us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md)

## Scope of Work
1. **Achievement Gallery Component (`services/campaign_analytics/ui/src/achievements/runefoble-achievement-gallery.ts`)**:
   - Implement `<runefoble-achievement-gallery>` with properties `campaignId`, `characterId`, `apiBaseUrl`, and `achievementsData`.
   - Render badge grid displaying badge icon, title, description, unlocked date, and rarity border accents (Bronze, Silver, Gold, Prismatic).
   - Render progress bars for locked/in-progress achievements (e.g. `[======    ] 60%`).
   - Category filtering controls: "All", "Combat", "Luck & Chaos", "Consistency".
2. **Achievement Gallery Styles (`services/campaign_analytics/ui/src/achievements/runefoble-achievement-gallery.styles.ts`)**:
   - Style badge cards with Bauhaus geometric angles, subtle drop shadows, and responsive grid layouts (< 130 lines).
3. **App Shell Analytics Hub Integration (`services/campaign_analytics/ui/src/runefoble-campaign-analytics.ts`)**:
   - Add "Achievements" tab button to `tabs-nav`.
   - Fetch campaign achievements from `/api/v1/analytics/campaigns/${this.campaignId}/achievements` and forward to `<runefoble-achievement-gallery>`.
4. **Storybook Stories (`services/campaign_analytics/ui/src/achievements/runefoble-achievement-gallery.stories.ts`)**:
   - Stories for empty state, full trophy collection, and in-progress milestones.
5. **Frontdoor Blackbox Verification (`tests/test_blackbox_campaign_achievements_ui.py`)**:
   - Verify component custom element registration, property updates, and filter interactions.

## Definition of Done
1. All new and modified TypeScript files remain strictly < 200 lines per Hard Invariant 6.
2. `<runefoble-achievement-gallery>` registered and rendered within `<runefoble-campaign-analytics>`.
3. Storybook stories compile and render cleanly with zero console errors.
4. Passes `pnpm run build` and `uv run pytest tests/test_blackbox_campaign_achievements_ui.py`.
