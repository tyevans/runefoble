---
id: 0269
title: Campaign Header Styles Modular Decomposition
status: Complete
created: 2026-09-27
dependencies: []
governing_adrs:
- ADR-0004
- ADR-0012
governing_prds: []
governing_stories: []
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/299
---
# TASK-0269: Campaign Header Styles Modular Decomposition

## Status
Refined

## Summary
Decompose `services/game_session/ui/src/campaigns/runefoble-campaign-header.styles.ts` (434 lines, 86.8% of limit) into modular CSS modules under `services/game_session/ui/src/campaigns/styles/` (`header_hero.styles.ts`, `header_meta.styles.ts`, `header_actions.styles.ts`), ensuring all extracted style modules remain strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/campaigns/runefoble-campaign-header.styles.ts` has grown to 434 lines—the largest file in the codebase and approaching the 500-line limit. It combines hero banner cover imagery, geometric Bauhaus fallback patterns, campaign metadata chips, responsive grids, and header action controls into a single monolithic style file. Further UI enhancements to session launchers or breadcrumb headers risk breaching Hard Invariant 6.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/develop-lit-components-in-storybook.md`: Lit CSS tagged template inheritance and styling conventions.
  - `docs/reference/design-tokens-and-themes.md`: Bauhaus geometric tokens and responsive breakpoints.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Modular CSS composition with Lit `css` tagged templates.
  - **ADR-0012: Design System Theming and Bauhaus Modernism**: Bauhaus design token usage and high-contrast styling invariants.

## Product & User Story References
- Technical debt refactoring directly supporting:
  - [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
  - [`us-0067-unified-campaign-detail-hero-header-and-tabbed-navigation.md`](../../user_stories/accepted/us-0067-unified-campaign-detail-hero-header-and-tabbed-navigation.md)

## Detailed Specification & Implementation Plan
1. **Style Module Decomposition (`services/game_session/ui/src/campaigns/styles/`)**:
   - `header_hero.styles.ts`: Host container, hero banner, cover image, and geometric pattern styles (< 120 lines).
   - `header_meta.styles.ts`: Title typography, description, setting/system tags, DM badges, and member chips (< 130 lines).
   - `header_actions.styles.ts`: Action button bar, launch session CTA, edit/delete actions, and responsive breakpoints (< 130 lines).
2. **Aggregator Export (`runefoble-campaign-header.styles.ts`)**:
   - Compose the modular styles into `campaignHeaderStyles = [headerHeroStyles, headerMetaStyles, headerActionsStyles]` (< 40 lines).
3. **Verification**:
   - Verify Storybook stories for `<runefoble-campaign-header>` pass and visual layout is preserved.

## INVEST Criteria Evaluation
- **Independent (I)**: Pure CSS decomposition without affecting component logic or backend APIs.
- **Negotiable (N)**: Granularity of extracted style groupings can be adjusted.
- **Valuable (V)**: Eliminates file length invariant risk for the largest file in the repository (434 lines).
- **Estimable (E)**: Pure mechanical refactoring and story visual verification.
- **Small (S)**: Target files are all under 150 lines.
- **Testable (T)**: Storybook visual regression checks and frontend build checks.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `runefoble-campaign-header.styles.ts` reduced to < 50 lines.
2. All extracted style modules under `services/game_session/ui/src/campaigns/styles/` strictly < 150 lines.
3. Storybook stories for `<runefoble-campaign-header>` render without regression.
4. Code passes lint and typecheck (`pnpm run lint` and `pnpm run build`).
