---
id: '0269'
title: Campaign Header Styles Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0012
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0269: Campaign Header Styles Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/ui/src/campaigns/runefoble-campaign-header.styles.ts` (434 lines, 86.8% of limit) into modular CSS modules under `services/game_session/ui/src/campaigns/styles/` (`header_hero.styles.ts`, `header_meta.styles.ts`, `header_actions.styles.ts`), ensuring all extracted style modules remain strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/campaigns/runefoble-campaign-header.styles.ts` has grown to 434 lines—the largest file in the codebase and approaching the 500-line limit. It combines hero banner cover imagery, geometric Bauhaus fallback patterns, campaign metadata chips, responsive grids, and header action controls into a single monolithic style file. Further UI enhancements to session launchers or breadcrumb headers risk breaching Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Modular CSS composition with Lit `css` tagged templates.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Bauhaus design token usage and high-contrast styling invariants.

## Scope of Work
1. **Style Module Decomposition (`services/game_session/ui/src/campaigns/styles/`)**:
   - `header_hero.styles.ts`: Host container, hero banner, cover image, and geometric pattern styles (< 120 lines).
   - `header_meta.styles.ts`: Title typography, description, setting/system tags, DM badges, and member chips (< 130 lines).
   - `header_actions.styles.ts`: Action button bar, launch session CTA, edit/delete actions, and responsive breakpoints (< 130 lines).
2. **Aggregator Export (`runefoble-campaign-header.styles.ts`)**:
   - Compose the modular styles into `campaignHeaderStyles = [headerHeroStyles, headerMetaStyles, headerActionsStyles]` (< 40 lines).
3. **Verification**:
   - Verify Storybook stories for `<runefoble-campaign-header>` pass and visual layout is preserved.

## Definition of Done
- `runefoble-campaign-header.styles.ts` reduced to < 50 lines.
- All extracted style modules under `services/game_session/ui/src/campaigns/styles/` strictly < 150 lines.
- Storybook stories for `<runefoble-campaign-header>` render without regression.
- Code passes lint and typecheck.
